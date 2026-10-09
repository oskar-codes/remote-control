from aiohttp import web
import logging
from aiohttp import web, WSMsgType
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from pathlib import Path
import subprocess
import sys
import webbrowser

logging.basicConfig(level=logging.INFO)

if sys.platform == "win32":
    from pycaw.pycaw import AudioUtilities  # Windows-only

PORT = 8000
WEB_DIR = Path(__file__).parent / "frontend" / "dist"
# Pixels of finger movement per scroll step: a wheel notch on Windows and Linux, 10 px on macOS
SCROLL_STEP = 10 if sys.platform == "darwin" else 30

keyboard = KeyboardController()
mouse = MouseController()

# Browser KeyboardEvent.key names -> pynput keys, single characters are typed as-is
KEYS = {
    "Enter": Key.enter,
    "Backspace": Key.backspace,
    "Tab": Key.tab,
    "Escape": Key.esc,
    "Delete": Key.delete,
    "ArrowUp": Key.up,
    "ArrowDown": Key.down,
    "ArrowLeft": Key.left,
    "ArrowRight": Key.right,
    "F5": Key.f5,
    "F11": Key.f11,
    "MediaPlayPause": Key.media_play_pause,
}
BUTTONS = {"left": Button.left, "right": Button.right}

# On macOS and Linux pynput drops the fractional part of scroll steps, so leftovers
# are kept here and added to the next scroll instead of being lost
scroll_leftover = {"x": 0.0, "y": 0.0}


def whole_steps(axis, steps):
    total = scroll_leftover[axis] + steps
    scroll_leftover[axis] = total - int(total)
    return int(total)


volume_process = None


def set_volume(percent):
    global volume_process
    percent = max(0, min(100, round(float(percent))))  # also keeps arbitrary input out of the commands below
    if sys.platform == "win32":
        speakers = AudioUtilities.GetSpeakers()
        if speakers is not None:
            # Check if muted
            if percent > 0 and speakers.EndpointVolume.GetMute():
                speakers.EndpointVolume.SetMute(0, None)
            elif percent == 0 and not speakers.EndpointVolume.GetMute():
                speakers.EndpointVolume.SetMute(1, None)
            speakers.EndpointVolume.SetMasterVolumeLevelScalar(percent / 100, None)
        else:
            logging.warning("Could not get speakers to set volume")
        return

    if sys.platform == "darwin":
        command = ["osascript", "-e", f"set volume output volume {percent}"]
    else:
        command = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"]
    # Dragging the slider sends many updates and these commands take a moment (osascript
    # especially), so don't wait for them: stop a still-running older one, the newest wins
    if volume_process and volume_process.poll() is None:
        volume_process.kill()
    volume_process = subprocess.Popen(command)


def handle_event(data):
    print(f"Received event: {data}")
    match data["type"]:
        case "key":
            key = data["key"]
            if key in KEYS:
                keyboard.tap(KEYS[key])
            elif len(key) == 1:
                keyboard.type(key)
        case "click":
            mouse.click(BUTTONS[data["button"]])
        case "move":
            mouse.move(data["dx"], data["dy"])
        case "scroll":
            # The frontend sends positive dy for scrolling down, pynput scrolls up on positive dy
            dx, dy = data["dx"] / SCROLL_STEP, -data["dy"] / SCROLL_STEP
            if sys.platform != "win32":  # Windows handles fractional steps itself, for smooth scrolling
                dx, dy = whole_steps("x", dx), whole_steps("y", dy)
            mouse.scroll(dx, dy)
        case "shortcut":
            url = data["url"]
            webbrowser.open(url)
        case "volume":
            set_volume(data["value"])

app = web.Application()

async def index(_: web.Request) -> web.FileResponse:
	return web.FileResponse(WEB_DIR / "index.html")


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    speakers = AudioUtilities.GetSpeakers()
    if speakers is not None:
        logging.info("Sending initial volume")
        await ws.send_json({"type": "volume", "value": round(speakers.EndpointVolume.GetMasterVolumeLevelScalar() * 100)})

    async for msg in ws:  # loops until the client disconnects
        if msg.type == WSMsgType.TEXT:
            handle_event(msg.json())
    return ws


app.router.add_get("/", index)
app.router.add_static("/assets", WEB_DIR / "assets")
app.router.add_get("/ws", ws_handler)
web.run_app(app, host="", port=PORT)