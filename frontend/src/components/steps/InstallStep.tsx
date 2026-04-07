import type { LogEntry, PendingPrompt } from '../../types';
import { LogViewer } from '../LogViewer';
import { PromptOverlay } from '../PromptOverlay';

interface InstallStepProps {
  logs: LogEntry[];
  prompt: PendingPrompt | null;
  onRespond: (value: unknown) => void;
  onRespondConfirm: (value: boolean) => void;
  onChooseDir?: () => Promise<string | null>;
}

export function InstallStep({ logs, prompt, onRespond, onRespondConfirm, onChooseDir }: InstallStepProps) {
  return (
    <div className="flex flex-col gap-5 h-full">
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-1">Install WVD</h2>
        <p className="text-xs text-text-secondary">
          Verifying the extracted file and choosing where to save it.
        </p>
      </div>

      <div className="bg-surface-100 rounded-lg border border-surface-300 p-4">
        <div className="flex items-center gap-3">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-accent shrink-0">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="1.5"/>
            <polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
          <div>
            <p className="text-sm text-text-primary">WVD file extracted successfully</p>
            <p className="text-xs text-text-muted">Choose a destination to save your device.wvd file</p>
          </div>
        </div>
      </div>

      {/* Prompt for destination */}
      {prompt && (
        <PromptOverlay
          prompt={prompt}
          onRespond={onRespond}
          onRespondConfirm={onRespondConfirm}
          onChooseDir={onChooseDir}
        />
      )}

      <div className="flex-1 min-h-0">
        <LogViewer logs={logs} maxHeight="180px" />
      </div>
    </div>
  );
}
