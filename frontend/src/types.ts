// ─── Backend event types ────────────────────────────────────────────────────

export interface StepEvent {
  event: 'step';
  step: number;
  total: number;
  title: string;
}

export interface MessageEvent {
  event: 'info' | 'success' | 'error' | 'warn' | 'fatal' | 'log';
  message: string;
}

export interface ProgressEvent {
  event: 'progress';
  percent: number;
  label: string;
}

export interface PromptChoiceEvent {
  event: 'prompt_choice';
  id: string;
  question: string;
  options: string[];
  default: number;
}

export interface PromptConfirmEvent {
  event: 'prompt_confirm';
  id: string;
  question: string;
  default: boolean;
}

export interface PromptPathEvent {
  event: 'prompt_path';
  id: string;
  question: string;
}

export interface StatusEvent {
  event: 'status';
  status: 'ready' | 'running' | 'finished' | 'error';
}

export interface DoneEvent {
  event: 'done';
  wvd_path: string;
}

export interface PongEvent {
  event: 'pong';
}

export interface CommandBlockEvent {
  event: 'command_block';
  command: string;
  description: string;
}

export interface PreflightResultEvent {
  event: 'preflight_result';
  ok: boolean;
  missing: string[];
}

export type BackendEvent =
  | StepEvent
  | MessageEvent
  | ProgressEvent
  | PromptChoiceEvent
  | PromptConfirmEvent
  | PromptPathEvent
  | StatusEvent
  | DoneEvent
  | PongEvent
  | CommandBlockEvent
  | PreflightResultEvent;

// ─── Wizard state ───────────────────────────────────────────────────────────

export type WizardStep =
  | 'welcome'
  | 'environment'
  | 'device'
  | 'extraction'
  | 'install'
  | 'done';

export const WIZARD_STEPS: WizardStep[] = [
  'welcome',
  'environment',
  'device',
  'extraction',
  'install',
  'done',
];

export const WIZARD_LABELS: Record<WizardStep, string> = {
  welcome: 'Welcome',
  environment: 'Environment',
  device: 'Device',
  extraction: 'Extraction',
  install: 'Install',
  done: 'Done',
};

// ─── Log entry ──────────────────────────────────────────────────────────────

export interface LogEntry {
  id: number;
  type: 'info' | 'success' | 'error' | 'warn' | 'log' | 'command';
  message: string;
  command?: string;
  timestamp: number;
}

// ─── Options ────────────────────────────────────────────────────────────────

export interface ExtractionOptions {
  timeout: number;
  output: string;
  device?: string;
  noCreate: boolean;
  keepAvd: boolean;
}

// ─── Pending prompt ─────────────────────────────────────────────────────────

export interface PendingPrompt {
  type: 'choice' | 'confirm' | 'path';
  id: string;
  question: string;
  options?: string[];
  default?: number | boolean;
}

// ─── Electron API type (must match preload.cts) ─────────────────────────────

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

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
