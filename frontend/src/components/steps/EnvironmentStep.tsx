import type { LogEntry } from '../../types';
import { ProgressBar } from '../ProgressBar';
import { LogViewer } from '../LogViewer';

interface EnvironmentStepProps {
  logs: LogEntry[];
  progress: { percent: number; label: string } | null;
  pipelineStatus: string;
  onRetry: () => void;
}

interface CheckItem {
  label: string;
  status: 'pending' | 'pass' | 'fail' | 'warn';
  detail?: string;
}

function deriveChecks(logs: LogEntry[]): CheckItem[] {
  const checks: CheckItem[] = [
    { label: 'Platform detected', status: 'pending' },
    { label: 'Python version', status: 'pending' },
    { label: 'ADB available', status: 'pending' },
    { label: 'WSL2 bridge (if applicable)', status: 'pending' },
  ];

  for (const log of logs) {
    const msg = log.message.toLowerCase();
    if (msg.includes('platform:')) {
      checks[0].status = 'pass';
      checks[0].detail = log.message.split('Platform:')[1]?.trim() || log.message;
    }
    if (msg.includes('python version ok')) {
      checks[1].status = 'pass';
    }
    if (msg.includes('adb found') || msg.includes('using adb') || (msg.includes('adb') && log.type === 'success')) {
      checks[2].status = 'pass';
      checks[2].detail = log.message;
    }
    if (msg.includes('adb') && log.type === 'error') {
      checks[2].status = 'fail';
      checks[2].detail = log.message;
    }
    if (msg.includes('wsl2') && log.type === 'success') {
      checks[3].status = 'pass';
    }
    if (msg.includes('not running in wsl') || msg.includes('not wsl')) {
      checks[3].status = 'pass';
      checks[3].detail = 'Not applicable';
    }
    if (msg.includes('all prerequisites met')) {
      // Mark remaining pending as pass
      checks.forEach(c => { if (c.status === 'pending') c.status = 'pass'; });
    }
  }

  return checks;
}

const STATUS_ICONS: Record<CheckItem['status'], { icon: string; color: string }> = {
  pending: { icon: '○', color: 'text-text-muted' },
  pass: { icon: '✓', color: 'text-green-400' },
  fail: { icon: '✗', color: 'text-red-400' },
  warn: { icon: '⚠', color: 'text-yellow-400' },
};

export function EnvironmentStep({ logs, progress, pipelineStatus, onRetry }: EnvironmentStepProps) {
  const checks = deriveChecks(logs);
  const hasFailed = pipelineStatus === 'error';

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-1">Environment Check</h2>
        <p className="text-xs text-text-secondary">
          Verifying your system has everything needed for CDM extraction.
        </p>
      </div>

      {/* Checklist */}
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-4">
        <div className="flex flex-col gap-3">
          {checks.map((check, idx) => {
            const { icon, color } = STATUS_ICONS[check.status];
            return (
              <div key={idx} className="flex items-center gap-3">
                <span className={`text-base ${color} w-5 text-center ${check.status === 'pending' ? 'animate-pulse' : ''}`}>
                  {icon}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-text-primary">{check.label}</span>
                  {check.detail && (
                    <span className="ml-2 text-xs text-text-muted truncate">{check.detail}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {progress && (
        <ProgressBar percent={progress.percent} label={progress.label} />
      )}

      {/* Log details */}
      <div>
        <LogViewer logs={logs} maxHeight="200px" />
      </div>

      {/* Retry bar — only shown when the pipeline errored on this step */}
      {hasFailed && (
        <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          <span className="text-sm text-red-400">
            Environment check failed. Follow the steps above, then re-check.
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
