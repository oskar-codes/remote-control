import { sendMessage } from "./websocket.js";

const SENSITIVITY = 4;        // cursor pixels per pixel of finger movement
const SCROLL_SENSITIVITY = 1;   // scroll pixels per pixel of finger movement
const TAP_MAX_DURATION = 300;   // ms, longer touches aren't taps
const TAP_MAX_TRAVEL = 10;      // px of finger movement before a touch stops being a tap
const DOUBLE_TAP_WINDOW = 215;  // ms a tap's button stays down, waiting for a touch to drag it (measured on a laptop trackpad)

const pointers = new Map();  // pointerId -> last known position
let gesture = null;          // the current touch, from first finger down to last finger up
let releaseTimer = null;     // set while a tap's button is still down, waiting for another touch

// Movement is added to running totals and sent at most once per frame,
// so a burst of pointermove events turns into a single message
const pending = {
  move: { dx: 0, dy: 0 },
  scroll: { dx: 0, dy: 0 },
};
let flushScheduled = false;

function queue(type, dx, dy) {
  pending[type].dx += dx;
  pending[type].dy += dy;
  if (!flushScheduled) {
    flushScheduled = true;
    requestAnimationFrame(flush);
  }
}

function flush() {
  flushScheduled = false;
  for (const [type, total] of Object.entries(pending)) {
    // The OS only moves by whole pixels: send the integer part and keep the
    // fraction for later, so slow movements still add up instead of being lost
    const dx = Math.trunc(total.dx);
    const dy = Math.trunc(total.dy);
    if (dx === 0 && dy === 0) continue;
    total.dx -= dx;
    total.dy -= dy;
    sendMessage({ type, dx, dy });
  }
}

function release() {
  flush();  // let go where the cursor ended up, not before its last move
  sendMessage({ type: "release", button: "left" });
}

// Whether the current touch is still short and still enough to end up a tap
function mayBeTap(timeStamp) {
  return timeStamp - gesture.start <= TAP_MAX_DURATION && gesture.travel <= TAP_MAX_TRAVEL;
}

function catchUp() {
  queue("move", gesture.heldBack.dx, gesture.heldBack.dy);
  gesture.heldBack = null;
}

export function onPointerDown(event) {
  event.currentTarget.setPointerCapture(event.pointerId);  // keep tracking outside the trackpad
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

  if (pointers.size === 1) {
    gesture = { start: event.timeStamp, fingers: 1, travel: 0, buttonDown: releaseTimer !== null };
    if (gesture.buttonDown) {
      // Touching again right after a tap: its button is still down, so this touch drags or double-clicks
      clearTimeout(releaseTimer);
      releaseTimer = null;
      gesture.heldBack = { dx: 0, dy: 0 };
    }
  } else {
    gesture.fingers = Math.max(gesture.fingers, pointers.size);
    if (gesture.buttonDown) {
      // More fingers don't drag: let go, this becomes a scroll or right click
      gesture.buttonDown = false;
      gesture.heldBack = null;
      release();
    }
  }
}

export function onPointerMove(event, sensitivity = SENSITIVITY, scrollSensitivity = SCROLL_SENSITIVITY) {
  const last = pointers.get(event.pointerId);
  if (!last) return;  // e.g. a mouse hovering without a button pressed

  const dx = event.clientX - last.x;
  const dy = event.clientY - last.y;
  last.x = event.clientX;
  last.y = event.clientY;
  gesture.travel += Math.hypot(dx, dy);

  if (gesture.fingers === 1 && gesture.heldBack) {
    // This may still be the second tap of a double-click, which must land where the first
    // one did: hold the movement back, and catch up once it's clearly a drag
    gesture.heldBack.dx += dx * sensitivity;
    gesture.heldBack.dy += dy * sensitivity;
    if (!mayBeTap(event.timeStamp)) catchUp();
  } else if (gesture.fingers === 1) {
    queue("move", dx * sensitivity, dy * sensitivity);
  } else if (pointers.size === 2) {
    // Each finger reports its own moves, so halving them scrolls by their average.
    // Natural scrolling (content follows the fingers), with the same sign as
    // WheelEvent: positive dy scrolls down, positive dx scrolls right.
    queue("scroll", -dx / 2 * scrollSensitivity, -dy / 2 * scrollSensitivity);
  }
  // Otherwise it's 3+ fingers, or one finger left after a two-finger gesture: ignored,
  // so lifting fingers one at a time doesn't nudge the cursor
}

export function onPointerUp(event) {
  if (!pointers.delete(event.pointerId)) return;
  if (pointers.size > 0) return;  // wait for the last finger to lift

  const isTap = event.type === "pointerup" && mayBeTap(event.timeStamp);
  if (gesture.heldBack && !isTap) catchUp();  // a drag too short or slow to have caught up yet

  flush();  // the click must land where the cursor ended up, not before its last move
  if (gesture.buttonDown) {
    release();  // ends the drag, or the first tap's click
    if (isTap) sendMessage({ type: "click", button: "left" });  // and this second tap makes it a double-click
  } else if (isTap && gesture.fingers === 1) {
    // Press now but release later: the press takes effect right away, and a touch
    // coming right after can still drag with the button down
    sendMessage({ type: "press", button: "left" });
    releaseTimer = setTimeout(() => {
      releaseTimer = null;
      release();
    }, DOUBLE_TAP_WINDOW);
  } else if (isTap && gesture.fingers === 2) {
    sendMessage({ type: "click", button: "right" });
  }
  gesture = null;
}
