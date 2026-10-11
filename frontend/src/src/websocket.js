import { ref } from "vue";

// "connecting" | "connected" | "disconnected"
export const connectionStatus = ref("connecting");

// "unknown" until the server says whether it needs a password, then "required",
// "rejected" (wrong, or changed on the server since it was saved) or "ok"
export const authStatus = ref("unknown");

export function sendMessage(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

export function login(newPassword) {
  password = newPassword;
  sendMessage({ type: "password", password });
}

// Stored rather than set on the socket, so it survives reconnects (each one creates a new socket)
export function registerMessageHandler(handler) {
  messageHandler = handler;
}

let ws;
let retryDelay = 500;
let messageHandler = null;
// Kept for the browser tab's lifetime, so reloads and reconnects log back in by themselves
let password = sessionStorage.getItem("password") ?? "";

// Every new connection has to log in, the server tells which with "password_required"
function handleAuthMessage(data) {
  switch (data.type) {
    case "password_required":
      if (!data.required) authStatus.value = "ok";
      else if (password) sendMessage({ type: "password", password });
      else authStatus.value = "required";
      break;
    case "password_accepted":
      authStatus.value = "ok";
      sessionStorage.setItem("password", password);  // only saved once it's known to work
      break;
    case "password_rejected":
      authStatus.value = "rejected";
      password = "";
      sessionStorage.removeItem("password");
      break;
  }
}

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
    console.log("received message:", data);
    handleAuthMessage(data);
    if (messageHandler) messageHandler(data);
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

