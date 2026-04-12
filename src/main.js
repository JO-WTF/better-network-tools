import { createApp } from "vue";
import App from "./App.vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import "./style.css";
import "mapbox-gl/dist/mapbox-gl.css";

const app = createApp(App);

// Suppress ResizeObserver loop limit exceeded error
const handleResizeError = (e) => {
  const suppressedErrors = [
    'ResizeObserver loop completed with undelivered notifications.',
    'ResizeObserver loop limit exceeded',
    'this.errorCb is not a function'
  ];
  if (e.message && suppressedErrors.some(msg => e.message.includes(msg))) {
    e.stopImmediatePropagation();
    return;
  }
};

window.addEventListener('error', handleResizeError);
window.addEventListener('unhandledrejection', (e) => {
  const suppressedErrors = [
    'ResizeObserver loop completed with undelivered notifications.',
    'ResizeObserver loop limit exceeded',
    'this.errorCb is not a function'
  ];
  if (e.reason && e.reason.message && suppressedErrors.some(msg => e.reason.message.includes(msg))) {
    e.stopImmediatePropagation();
  }
});

app.use(Antd);
app.mount("#app");
