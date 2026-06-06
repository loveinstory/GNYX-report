const { app, BrowserWindow } = require("electron");

const rendererUrl = process.env.AWK_RENDERER_URL || "http://127.0.0.1:5188";

function createWindow() {
  const win = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 1180,
    minHeight: 760,
    title: "安为康功能医学报告生成平台",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadURL(rendererUrl);
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

