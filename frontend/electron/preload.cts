import { contextBridge, ipcRenderer } from 'electron';

export interface ElectronAPI {
  python: {
    send: (command: Record<string, unknown>) => Promise<void>;
    onEvent: (callback: (data: Record<string, unknown>) => void) => () => void;
    onStatus: (callback: (status: string) => void) => () => void;
  };
  window: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
    isMaximized: () => Promise<boolean>;
  };
  dialog: {
    chooseDir: () => Promise<string | null>;
  };
  shell: {
    openPath: (filePath: string) => Promise<void>;
    openPowerShellAdmin: (command: string) => Promise<void>;
    openExternal: (url: string) => Promise<void>;
  };
}

contextBridge.exposeInMainWorld('electronAPI', {
  python: {
    send: (command: Record<string, unknown>) => ipcRenderer.invoke('python:send', command),
    onEvent: (callback: (data: Record<string, unknown>) => void) => {
      const handler = (_event: unknown, data: Record<string, unknown>) => callback(data);
      ipcRenderer.on('python:event', handler);
      return () => ipcRenderer.removeListener('python:event', handler);
    },
    onStatus: (callback: (status: string) => void) => {
      const handler = (_event: unknown, status: string) => callback(status);
      ipcRenderer.on('python:status', handler);
      return () => ipcRenderer.removeListener('python:status', handler);
    },
  },
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
  },
  dialog: {
    chooseDir: () => ipcRenderer.invoke('dialog:chooseDir'),
  },
  shell: {
    openPath: (filePath: string) => ipcRenderer.invoke('shell:openPath', filePath),
    openPowerShellAdmin: (command: string) => ipcRenderer.invoke('shell:openPowerShellAdmin', command),
    openExternal: (url: string) => ipcRenderer.invoke('shell:openExternal', url),
  },
});
