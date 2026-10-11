from aiohttp import web
import logging
from aiohttp import web, WSMsgType
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from pathlib import Path
import os
import re
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

if sys.platform.startswith("linux"):
    # pynput's typing of characters is ignored by many X11 apps, see x11_typing.py
    from x11_typing import type_character
else:
    type_character = keyboard.type

# On macOS and Linux pynput drops the fractional part of scroll steps, so leftovers
# are kept here and added to the next scroll instead of being lost
scroll_leftover = {"x": 0.0, "y": 0.0}

def whole_steps(axis, steps):
    total = scroll_leftover[axis] + steps
    scroll_leftover[axis] = total - int(total)
    return int(total)


def run_command(command):
    """Returns the command's output, or None if it isn't installed or fails"""
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=2, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def set_volume(percent):
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
        run_command(["osascript", "-e", f"set volume output volume {percent}"])
        return

    # Like on Windows, 0 mutes and anything above unmutes
    backend, _ = linux_volume()
    mute = "1" if percent == 0 else "0"
    if backend == "wpctl":
        run_command(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"])
        run_command(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", mute])
    elif backend == "pactl":
        run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"])
        run_command(["pactl", "set-sink-mute", "@DEFAULT_SINK@", mute])
    else:
        logging.warning("Could not set the volume: neither wpctl (PipeWire) nor pactl (PulseAudio) worked")


def linux_volume():
    """Returns which of wpctl (PipeWire, the default on current distros) or pactl (PulseAudio)
    works, and the volume in percent it reads, or (None, None) if neither does. A backend only
    counts once it reads the volume, because wpctl exits with 0 even when it fails."""
    output = run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])  # e.g. "Volume: 0.40"
    if output and (match := re.search(r"Volume: ([\d.]+)", output)):
        return "wpctl", round(float(match[1]) * 100)
    output = run_command(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])  # e.g. "Volume: front-left: 26214 /  40% / ..."
    if output and (match := re.search(r"(\d+)%", output)):
        return "pactl", int(match[1])
    return None, None


def get_volume():
    """Current output volume in percent, or None if it can't be read"""
    if sys.platform == "win32":
        speakers = AudioUtilities.GetSpeakers()
        return round(speakers.EndpointVolume.GetMasterVolumeLevelScalar() * 100) if speakers else None
    if sys.platform == "darwin":
        output = run_command(["osascript", "-e", "output volume of (get volume settings)"])
        return int(output) if output and output.strip().isdigit() else None
    return linux_volume()[1]


async def send_volume(ws):
    volume = get_volume()
    if volume is not None:
        await ws.send_json({"type": "volume", "value": volume})

def handle_event(data, verbose=False):
    if verbose:
        print(f"Received event: {data}")
    match data["type"]:
        case "key":
            key = data["key"]
            if key in KEYS:
                keyboard.tap(KEYS[key])
            elif len(key) == 1:
                type_character(key)
        case "command":
            *modifiers, key = COMMANDS[data["name"]]
            with keyboard.pressed(*modifiers):  # releases the modifiers even if the tap fails
                if isinstance(key, str):
                    type_character(key)
                else:
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

async def ws_handler(request, password: str = "", verbose: bool = False) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_json({"type": "password_required", "required": bool(password)})

    # Each connection logs in once, after that all its messages are trusted
    authenticated = not password
    if authenticated:
        await send_volume(ws)

    async for msg in ws:  # loops until the client disconnects
        if msg.type != WSMsgType.TEXT:
            continue
        data = msg.json()
        if authenticated:
            handle_event(data, verbose=verbose)
        elif data["type"] == "password":
            authenticated = data["password"] == password
            if authenticated:
                if verbose:
                    print("Password accepted, client connected.")
                await ws.send_json({"type": "password_accepted"})
                await send_volume(ws)
            else:
                if verbose:
                    print("Password rejected, client attempted to connect with incorrect password.")
                await ws.send_json({"type": "password_rejected"})
        # Anything else sent before logging in is ignored
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


def main(port, web_dir_relative, password, verbose):
    global app, web_dir

    web_dir = Path(web_dir_relative).resolve()

    if sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland":
        logging.warning("Wayland session detected: pynput sends input through X11, so it may only reach "
                        "XWayland apps or nothing at all. Log into an X11 session for full control.")

    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    app = web.Application()
    print(f"Server starting at http://{get_ip()}:{port}")

    lambda_handler = lambda request: ws_handler(request, password=password, verbose=verbose)

    app.router.add_get("/", index)
    app.router.add_static("/assets", web_dir / "assets")
    app.router.add_get("/ws", lambda_handler)
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
        help="Password for connecting to the server (leave empty for no password, default is empty)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()
    main(args.port, args.web_dir, args.password, args.verbose)
