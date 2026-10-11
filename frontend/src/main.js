import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './src/websocket.js'
import './src/main.css'

// iOS Safari ignores user-scalable=no in the viewport, so block its pinch-zoom gesture directly
document.addEventListener('gesturestart', (event) => event.preventDefault())

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
