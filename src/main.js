import { createApp } from "vue";
import App from "./App.vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import "./style.css";
import "mapbox-gl/dist/mapbox-gl.css";

const app = createApp(App);

// Suppress ResizeObserver loop limit exceeded error
const debounce = (fn, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
};

const handleResizeError = debounce((e) => {
  if (e.message === 'ResizeObserver loop completed with undelivered notifications.' || e.message === 'ResizeObserver loop limit exceeded') {
    e.stopImmediatePropagation();
  }
}, 100);

window.addEventListener('error', handleResizeError);
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason && (e.reason.message === 'ResizeObserver loop completed with undelivered notifications.' || e.reason.message === 'ResizeObserver loop limit exceeded')) {
    e.stopImmediatePropagation();
  }
});

app.use(Antd);
app.mount("#app");
