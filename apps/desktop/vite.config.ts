import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = {
  target: "http://192.168.20.243:8111",
  changeOrigin: true,
  rewrite: (path: string) => path.replace(/^\/api/, "")
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5188,
    strictPort: true,
    proxy: {
      "/api": apiProxy
    }
  },
  preview: {
    host: "0.0.0.0",
    port: 5188,
    strictPort: true,
    proxy: {
      "/api": apiProxy
    }
  }
});
