import { ref } from "vue";

// "connecting" | "connected" | "disconnected"
export const connectionStatus = ref("connecting");

export function sendMessage(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

// Stored rather than set on the socket, so it survives reconnects (each one creates a new socket)
export function registerMessageHandler(handler) {
  messageHandler = handler;
}

let ws;
let retryDelay = 500;
let messageHandler = null;

function connect() {
  connectionStatus.value = "connecting";
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    console.log("connected");
    connectionStatus.value = "connected";
    retryDelay = 500;  // reset after a successful connection
  };
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (messageHandler) messageHandler(data);
    else console.log(data);
  };
  ws.onclose = () => {
    console.log(`disconnected, retrying in ${retryDelay} ms`);
    connectionStatus.value = "disconnected";
    setTimeout(connect, retryDelay);
    retryDelay = Math.min(retryDelay * 2, 5000);  // exponential backoff, capped at 5 s
  };
  ws.onerror = () => ws.close();  // make sure onclose runs
}

// Only connect if not in dev mode
if (import.meta.env.PROD) connect();

