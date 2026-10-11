# Remote Control
A simple tool to remotely control a PC, over a local WiFi network. Specifically designed for media player servers.

## Usage
Clone the repository:
```sh
git clone https://github.com/oskar-codes/remote-control.git
```
Build the frontend UI:
```
cd frontend
npm install
npm run build
```
Install the server's dependencies (from the root directory):
```
pip install -r requirements.txt
```
Start the server (from the root directory):
```
python -m server
```
This will display the server’s local IP address, to which you can connect any device that is on the WiFi network.

### Linux
- **Use an X11 session.** On Wayland (the default on recent Ubuntu and Fedora), keyboard and mouse input may only reach some apps, or none. Choose the X11 / "Xorg" session on the login screen.
- **Install the dependencies in a virtual environment**, since most distributions block system-wide `pip install`. On Linux, pip also compiles `evdev` (needed by `pynput`), which requires a C compiler and the Python headers. On Debian/Ubuntu:
  ```sh
  sudo apt install python3-venv python3-dev gcc
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python -m server
  ```
- **Start the server from inside the desktop session** (for example as a startup application), not as a system service: it needs the session's display to send input.
- The volume slider uses `wpctl` (PipeWire, the default on current distributions) or `pactl` (PulseAudio), whichever works.

Server options:
```
usage: server.py [-h] [--port PORT] [--web-dir WEB_DIR] [--password PASSWORD]

Remote Control Server

options:
  -h, --help           show this help message and exit
  --port PORT          Port to run the server on (default: 8000)
  --web-dir WEB_DIR    Directory containing the frontend web files (default: frontend/dist)
  --password PASSWORD  Password for connecting to the server (leave empty for no password, default is empty)
```
