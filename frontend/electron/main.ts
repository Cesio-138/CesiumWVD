import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import { PythonBridge } from './python-bridge.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: BrowserWindow | null = null;
let pythonBridge: PythonBridge | null = null;
let bridgeStatus = 'disconnected';

const isDev = !app.isPackaged;

function getBackendRoot(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend');
  }
  // dev: __dirname is frontend/dist-electron, go up to wvd-extractor/
  return path.resolve(__dirname, '..', '..');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 640,
    minWidth: 800,
    minHeight: 560,
    frame: false,
    backgroundColor: '#121212',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5174');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  // Re-send current bridge status once renderer finishes loading (race condition fix)
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow?.webContents.send('python:status', bridgeStatus);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── Python Bridge ───────────────────────────────────────────────────────────

function startPythonBridge() {
  const backendRoot = getBackendRoot();
  pythonBridge = new PythonBridge(backendRoot);

  pythonBridge.on('event', (data: Record<string, unknown>) => {
    mainWindow?.webContents.send('python:event', data);
  });

  pythonBridge.on('error', (err: string) => {
    mainWindow?.webContents.send('python:event', { event: 'error', message: err });
  });

  pythonBridge.on('status', (status: string) => {
    bridgeStatus = status;
    mainWindow?.webContents.send('python:status', status);
  });

  pythonBridge.start();
}

// ─── IPC Handlers ────────────────────────────────────────────────────────────

ipcMain.handle('python:send', (_event, command: Record<string, unknown>) => {
  pythonBridge?.send(command);
});

ipcMain.handle('window:minimize', () => mainWindow?.minimize());
ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.handle('window:close', () => mainWindow?.close());
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);

ipcMain.handle('dialog:chooseDir', async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
  });
  return result.canceled ? null : result.filePaths[0] ?? null;
});

ipcMain.handle('shell:openPath', (_event, filePath: string) => {
  shell.openPath(filePath);
});

ipcMain.handle('shell:openPowerShellAdmin', (_event, command: string) => {
  // Works on WSL2 (powershell.exe is on PATH) and native Windows.
  // Opens an elevated PowerShell window that runs the command and stays open.
  const safeCmd = command.replace(/'/g, "''");
  const psArgs = [
    '-Command',
    `Start-Process powershell -Verb RunAs -ArgumentList '-NoExit', '-Command', '${safeCmd}'`,
  ];
  const ps = spawn('powershell.exe', psArgs, { detached: true, stdio: 'ignore' });
  ps.unref();
});

// ─── Lifecycle ───────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow();
  startPythonBridge();
});

app.on('window-all-closed', () => {
  pythonBridge?.stop();
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
