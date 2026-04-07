import type { LogEntry, PendingPrompt } from '../../types';
import { ProgressBar } from '../ProgressBar';
import { LogViewer } from '../LogViewer';
import { PromptOverlay } from '../PromptOverlay';

interface DeviceStepProps {
  logs: LogEntry[];
  progress: { percent: number; label: string } | null;
  prompt: PendingPrompt | null;
  onRespond: (value: unknown) => void;
  onRespondConfirm: (value: boolean) => void;
  pipelineStatus: string;
  onRetry: () => void;
}

export function DeviceStep({ logs, progress, prompt, onRespond, onRespondConfirm, pipelineStatus, onRetry }: DeviceStepProps) {
  const isDownloading = progress !== null && progress.label.toLowerCase().includes('download');
  const isBooting = logs.some(l => l.message.toLowerCase().includes('waiting for emulator') || l.message.toLowerCase().includes('boot'));
  const hasFailed = pipelineStatus === 'error';

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-1">Android Device</h2>
        <p className="text-xs text-text-secondary">
          Connecting to a device or creating a temporary emulator.
        </p>
      </div>

      {/* Status card */}
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-3 h-3 rounded-full ${isBooting ? 'bg-yellow-400 animate-pulse' : isDownloading ? 'bg-accent animate-pulse' : 'bg-surface-400'}`} />
          <span className="text-sm text-text-primary">
            {isDownloading
              ? 'Downloading system image...'
              : isBooting
                ? 'Booting emulator...'
                : 'Setting up device...'}
          </span>
        </div>
        {progress && (
          <ProgressBar
            percent={progress.percent}
            label={progress.label}
            indeterminate={isBooting && !isDownloading}
          />
        )}
        {isBooting && !progress && (
          <ProgressBar percent={null} label="Waiting for emulator to boot..." indeterminate />
        )}
      </div>

      {/* Prompt area */}
      {prompt && (
        <PromptOverlay
          prompt={prompt}
          onRespond={onRespond}
          onRespondConfirm={onRespondConfirm}
        />
      )}

      <div>
        <LogViewer logs={logs} maxHeight="180px" />
      </div>

      {/* Retry bar */}
      {hasFailed && (
        <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          <span className="text-sm text-red-400">
            Device setup failed. Check that the emulator is running, then re-check.
          </span>
          <button
            onClick={onRetry}
            className="ml-4 shrink-0 px-4 py-1.5 rounded-lg bg-accent text-black text-sm font-semibold hover:bg-accent-hover transition-colors"
          >
            Re-check ↺
          </button>
        </div>
      )}
    </div>
  );
}
