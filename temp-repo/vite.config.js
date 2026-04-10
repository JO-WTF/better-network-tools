import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const DEV_HOST = "0.0.0.0";
const DEV_DOMAIN = "sim.isc.huawei.com";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: DEV_HOST,
    allowedHosts: [DEV_DOMAIN],
  },
});
