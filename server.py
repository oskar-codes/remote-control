from aiohttp import web
import logging
from aiohttp import web, WSMsgType
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from pathlib import Path
import subprocess
import sys
import webbrowser
import socket
import argparse

logging.basicConfig(level=logging.INFO)

if sys.platform == "win32":
    from pycaw.pycaw import AudioUtilities  # Windows-only

PORT_DEFAULT = 8000
WEB_DIR_DEFAULT = Path(__file__).parent / "frontend" / "dist"
# Pixels of finger movement per scroll step: a wheel notch on Windows and Linux, 10 px on macOS
SCROLL_STEP = 10 if sys.platform == "darwin" else 30

web_dir = WEB_DIR_DEFAULT

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

# Modifier most shortcuts use (Cmd on macOS, Ctrl elsewhere)
PRIMARY = Key.cmd if sys.platform == "darwin" else Key.ctrl

# Pre-written shortcuts the frontend triggers by name: every key but the last is held
# down while the last one is tapped. Add new ones here and send their name from a button.
COMMANDS = {
    "new_tab": (PRIMARY, "t"),
    "focus_address_bar": (PRIMARY, "l"),
    "close_tab": (PRIMARY, "w"),
    "next_tab": (Key.ctrl, Key.tab),
    "previous_tab": (Key.shift, Key.ctrl, Key.tab),
}

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
        case "command":
            *modifiers, key = COMMANDS[data["name"]]
            with keyboard.pressed(*modifiers):  # releases the modifiers even if the tap fails
                keyboard.tap(key)
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

async def index(_: web.Request) -> web.FileResponse:
	return web.FileResponse(web_dir / "index.html")


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    speakers = AudioUtilities.GetSpeakers()
    if speakers is not None:
        await ws.send_json({"type": "volume", "value": round(speakers.EndpointVolume.GetMasterVolumeLevelScalar() * 100)})

    async for msg in ws:  # loops until the client disconnects
        if msg.type == WSMsgType.TEXT:
            handle_event(msg.json())
    return ws

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def main(port, web_dir_relative, password):
    global app, web_dir

    web_dir = Path(web_dir_relative).resolve()

    app = web.Application()
    print(f"Server starting at http://{get_ip()}:{port}")

    app.router.add_get("/", index)
    app.router.add_static("/assets", web_dir / "assets")
    app.router.add_get("/ws", ws_handler)
    web.run_app(app, host="", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remote Control Server")
    parser.add_argument(
        "--port",
        type=int,
        default=PORT_DEFAULT,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--web-dir",
        type=str,
        default=WEB_DIR_DEFAULT,
        help="Directory containing the frontend web files (default: frontend/dist)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="", # No password by default
        help="Password for connecting to the server",
    )
    args = parser.parse_args()
    main(args.port, args.web_dir, args.password)
