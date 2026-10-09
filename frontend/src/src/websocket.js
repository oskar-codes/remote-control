import { ref } from "vue";

// "connecting" | "connected" | "disconnected"
export const connectionStatus = ref("connecting");

export function sendMessage(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

export function registerMessageHandler(handler) {
  if (!ws) throw new Error("WebSocket not connected yet");
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    handler(data);
  };
}

let ws;
let retryDelay = 500;

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
    console.log(data);
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

