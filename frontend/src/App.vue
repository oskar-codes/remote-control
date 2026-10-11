<script setup>
import playPauseIcon from './assets/play-pause.svg';
import focusIcon from './assets/focus.svg';
import closeIcon from './assets/close.svg';
import leftIcon from './assets/left.svg';
import rightIcon from './assets/right.svg';
import plusIcon from './assets/plus.svg';
</script>

<template>
  <main>
    <nav>
      <h1>Remote</h1>
      <div class="status" :class="status">
        {{ status }}
        <span class="dot"></span>
      </div>
    </nav>
    <input
      ref="keyboardInput"
      class="keyboard-input"
      type="text"
      autocomplete="off"
      autocorrect="off"
      autocapitalize="off"
      spellcheck="false"
      @input="onInput"
      @keydown="onKeyDown"
      @blur="resetBuffer"
    />
    <div class="inputs">
      <div
        class="trackpad"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove($event, sensitivity, scrollSensitivity)"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @contextmenu.prevent
      ></div>
      
      <div class="setting">
        <p><span>Volume</span> <span>{{ volume }}</span></p>
        <input :disabled="disconnected" v-model.number="volume" type="range" min="0" max="100" @change="sendVolume" />
      </div>

      <!-- <div class="input-row">
      </div> -->
      <div class="input-row">
        <button :disabled="disconnected" @click="sendCommand('focus_address_bar')">
          <img :src="focusIcon" alt="Focus" />
        </button>
        <button :disabled="disconnected" @click="sendCommand('close_tab')">
          <img :src="closeIcon" alt="Close" />
        </button>
        <button :disabled="disconnected" @click="sendCommand('new_tab')">
          <img :src="plusIcon" alt="New Tab" />
        </button>
        <button :disabled="disconnected" @click="sendCommand('previous_tab')">
          <img :src="leftIcon" alt="Left" />
        </button>
        <button :disabled="disconnected" @click="sendCommand('next_tab')">
          <img :src="rightIcon" alt="Right" />
        </button>
      </div>
      <div class="input-row">
        <button @click="openKeyboard" :disabled="disconnected">Keyboard</button>
        <div class="input-row">
          <button :disabled="disconnected" @click="sendKey('MediaPlayPause')">
            <img :src="playPauseIcon" alt="Play/Pause" />
          </button>
          <button @click="openMore">More</button>
        </div>
      </div>
    </div>

    <div class="modal" v-if="moreOpen">
      <div class="content">
        <h2>Advanced keys</h2>
        <div class="input-row">
          <button :disabled="disconnected" @click="sendKey('Escape')">Esc</button>
          <button :disabled="disconnected" @click="sendKey('Tab')">Tab</button>
          <button :disabled="disconnected" @click="sendKey('Delete')">Del</button>
        </div>
        <div class="input-row">
          <button :disabled="disconnected" @click="sendKey('ArrowUp')">↑</button>
          <button :disabled="disconnected" @click="sendKey('ArrowDown')">↓</button>
          <button :disabled="disconnected" @click="sendKey('ArrowLeft')">←</button>
          <button :disabled="disconnected" @click="sendKey('ArrowRight')">→</button>
        </div>
        <!-- most useful F keys -->
        <div class="input-row">
          <button :disabled="disconnected" @click="sendKey('F5')">F5</button> <!-- refresh -->
          <button :disabled="disconnected" @click="sendKey('F11')">F11</button> <!-- fullscreen -->
        </div>


        <hr>
        <h2>Shortcuts</h2>
        <div class="input-row">
          <button :disabled="disconnected" @click="sendShortcut('https://google.com/')">Browser</button>
          <button :disabled="disconnected" @click="sendShortcut('https://oskar-codes.github.io/zmoviesz/')">ZMOVIESZ</button>
          <button :disabled="disconnected" @click="sendShortcut('https://www.hltv.org/')">HLTV</button>
        </div>

        <hr>
        <h2>Settings</h2>
        <div class="settings">
          <div class="setting">
            <p><span>Mouse Sensitivity</span> <span>{{ sensitivity }}</span></p>
            <input :disabled="disconnected" v-model.number="sensitivity" step="0.5" type="range" min="1" max="15" />
          </div>
          <div class="setting">
            <p><span>Scroll Sensitivity</span> <span>{{ scrollSensitivity }}</span></p>
            <input :disabled="disconnected" v-model.number="scrollSensitivity" step="0.5" type="range" min="0.5" max="5" />
          </div>
        </div>
  
        <button @click="closeMore">Close</button>
      </div>
    </div>

    <Transition name="fade">
      <div class="modal" v-if="showPasswordPrompt">
        <div class="content">
          <h2>Password Required</h2>
          <p>Please enter the password to connect to the remote control.</p>
          <p v-if="passwordRejected">That password didn't work, it may have changed on the server.</p>
          <input type="password" v-model="password" placeholder="Password" />
          <button @click="submitPassword">Submit</button>
        </div>
      </div>
    </Transition>

  </main>
</template>

<style scoped>
main {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh; /* the visible screen: on phones 100vh is taller while the browser toolbars show */
}

nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1em;
  background-color: #f3f4f6;
}

div.inputs {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1em;
  padding: 1em;
  height: 100%;
}

div.input-row img {
  width: 30%;
  aspect-ratio: 1/1;
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%,-50%);
  pointer-events: none;
}

div.input-row {
  display: flex;
  flex: 0.5;
  gap: 1em;
  width: 100%;
}

div.input-row > * {
  flex: 1;
  flex-basis: 0;
  width: 100%;
  position: relative;
}

div.trackpad {
  width: 100%;
  height: 100px;
  border: 1px solid #ccc;
  border-radius: 4px;
  flex: 4;
  /* no text selection or iOS long-press callout while dragging */
  user-select: none;
  touch-action: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
  text-transform: capitalize;
}

.dot {
  width: 0.6em;
  height: 0.6em;
  border-radius: 50%;
  background: gray;
}

.connected .dot {
  background: #22c55e;
}

.connecting .dot {
  background: #f59e0b;
}

.disconnected .dot {
  background: #ef4444;
}

/* Invisible but still focusable: with visibility: hidden or display: none the
   input can't take focus, so the native keyboard would never open */
.keyboard-input {
  position: fixed;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  padding: 0;
  border: 0;
  opacity: 0;
  pointer-events: none;
  font-size: 16px; /* iOS zooms the page when focusing inputs smaller than 16px */
}

div.modal {
  position: fixed;
  overflow-y: scroll;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: white;
  gap: 1em;
  display: flex;
  justify-content: center;
  align-items: center;
}

div.modal .content {
  width: 80%;
  margin: auto 0;
  display: flex;
  flex-direction: column;
  gap: 1em;
  padding: 1em;
}

div.modal .settings {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.setting {
  width: 100%;
}

.setting p {
  display: flex;
  justify-content: space-between;
  margin: 0;
}

input[type="range"] {
  width: 100%;
}

</style>

<script>
import { sendMessage, connectionStatus, authStatus, login, registerMessageHandler } from "./src/websocket.js";
import { onPointerDown, onPointerMove, onPointerUp } from "./src/trackpad.js";

// Keys that never change the input's text, so they're sent straight from keydown
const SPECIAL_KEYS = ["Enter", "Tab", "Escape", "Delete", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];

// Settings saved on the phone itself, with a default for the first visit
function loadSetting(name, fallback) {
  return Number(localStorage.getItem(name)) || fallback;
}

export default {
  name: "App",
  data() {
    return {
      typed: "",  // last known value of the hidden input, to diff against
      moreOpen: false,
      volume: 100,
      sensitivity: loadSetting("sensitivity", 4),
      scrollSensitivity: loadSetting("scrollSensitivity", 1),
      password: "",  // what's typed in the password prompt
    };
  },
  watch: {
    sensitivity(value) {
      localStorage.setItem("sensitivity", value);
    },
    scrollSensitivity(value) {
      localStorage.setItem("scrollSensitivity", value);
    }
  },
  mounted() {
    registerMessageHandler((data) => {
      if (data.type === "volume") {
        this.volume = data.value;
      }
    });
  },
  computed: {
    status() {
      return connectionStatus.value;
    },
    disconnected() {
      return this.status !== "connected";
    },
    showPasswordPrompt() {
      return authStatus.value === "required" || authStatus.value === "rejected";
    },
    passwordRejected() {
      return authStatus.value === "rejected";
    }
  },
  methods: {
    submitPassword() {
      login(this.password);
      this.password = "";
    },
    onPointerDown,
    onPointerMove,
    onPointerUp,
    openKeyboard() {
      this.$refs.keyboardInput.focus();
    },
    openMore() {
      this.moreOpen = true;
    },
    closeMore() {
      this.moreOpen = false;
    },
    sendKey(key) {
      sendMessage({
        type: 'key',
        key
      })
    },
    sendClick(button) {
      sendMessage({
        type: 'click',
        button
      })
    },
    sendShortcut(url) {
      sendMessage({
        type: 'shortcut',
        url
      })
    },
    // Only sent when the slider is released, the label still updates live through v-model
    sendVolume() {
      sendMessage({
        type: 'volume',
        value: this.volume
      })
    },
    sendCommand(name) {
      sendMessage({
        type: 'command',
        name
      })
    },
    // Mobile keyboards mostly report "Unidentified" on keydown and can edit whole
    // words at once (suggestions, autocorrect), so instead diff the input's value
    // and replay the change as backspaces followed by the newly typed characters.
    onInput(event) {
      const before = Array.from(this.typed);
      const after = Array.from(event.target.value);
      let common = 0;
      while (common < before.length && before[common] === after[common]) common++;

      for (let i = common; i < before.length; i++) this.sendKey("Backspace");
      for (const char of after.slice(common)) this.sendKey(char);
      this.typed = event.target.value;
    },
    onKeyDown(event) {
      // Backspace on an empty input fires no input event, so it has to be sent here
      const emptyBackspace = event.key === "Backspace" && event.target.value === "";
      if (!SPECIAL_KEYS.includes(event.key) && !emptyBackspace) return;

      event.preventDefault();  // keep the caret at the end and focus in the input
      this.sendKey(event.key);
      if (event.key === "Enter") this.resetBuffer();
    },
    resetBuffer() {
      this.$refs.keyboardInput.value = "";
      this.typed = "";
    }
  }
};
</script>
