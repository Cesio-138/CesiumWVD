import type { LogEntry } from '../../types';
import { ProgressBar } from '../ProgressBar';
import { LogViewer } from '../LogViewer';

interface ExtractionStepProps {
  logs: LogEntry[];
  progress: { percent: number; label: string } | null;
  backendStep: number;
  pipelineStatus: string;
  onRetry: () => void;
}

export function ExtractionStep({ logs, progress, backendStep, pipelineStatus, onRetry }: ExtractionStepProps) {
  const isError = pipelineStatus === 'error';

  const phases = [
    { label: 'Connect & root device', step: 4 },
    { label: 'Setup frida-server', step: 5 },
    { label: 'Extract Widevine CDM', step: 6 },
  ];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-1">CDM Extraction</h2>
        <p className="text-xs text-text-secondary">
          Rooting the device, setting up Frida, and extracting the Widevine module.
        </p>
      </div>

      {/* Sub-phases */}
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-4">
        <div className="flex flex-col gap-3">
          {phases.map((phase) => {
            const isActive = backendStep === phase.step;
            const isDone = backendStep > phase.step;
            const isFailed = isError && isActive;

            return (
              <div key={phase.step} className="flex items-center gap-3">
                <span className={`text-base w-5 text-center ${
                  isFailed ? 'text-red-400' :
                  isDone ? 'text-green-400' :
                  isActive ? 'text-accent animate-pulse' :
                  'text-text-muted'
                }`}>
                  {isFailed ? '✗' : isDone ? '✓' : isActive ? '◉' : '○'}
                </span>
                <span className={`text-sm ${isActive ? 'text-text-primary font-medium' : isDone ? 'text-text-secondary' : 'text-text-muted'}`}>
                  {phase.label}
                </span>
                {isActive && !isError && (
                  <span className="ml-auto text-xs text-accent">in progress</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {progress && (
        <ProgressBar percent={progress.percent} label={progress.label} />
      )}

      {/* Show indeterminate progress when extraction is running without specific progress */}
      {backendStep === 6 && !progress && !isError && (
        <ProgressBar
          percent={null}
          label="Waiting for CDM extraction... this may take 1-2 minutes"
          indeterminate
        />
      )}

      <div>
        <LogViewer logs={logs} maxHeight="200px" />
      </div>

      {isError && (
        <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          <span className="text-sm text-red-400">
            Extraction failed. Check the log, then try again.
          </span>
          <button
            onClick={onRetry}
            className="ml-4 shrink-0 px-4 py-1.5 rounded-lg bg-accent text-black text-sm font-semibold hover:bg-accent-hover transition-colors"
          >
            Try again ↺
          </button>
        </div>
      )}
    </div>
  );
}
