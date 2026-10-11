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
Start the server (from the root directory):
```
python -m server
```
This will display the server’s local IP address, to which you can connect any device that is on the WiFi network.

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
