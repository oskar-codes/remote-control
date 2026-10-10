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
