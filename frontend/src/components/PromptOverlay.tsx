import { useState } from 'react';
import type { PendingPrompt } from '../types';

interface PromptOverlayProps {
  prompt: PendingPrompt;
  onRespond: (value: unknown) => void;
  onRespondConfirm: (value: boolean) => void;
  onChooseDir?: () => Promise<string | null>;
}

export function PromptOverlay({ prompt, onRespond, onRespondConfirm, onChooseDir }: PromptOverlayProps) {
  const [pathValue, setPathValue] = useState('');

  if (prompt.type === 'choice') {
    return (
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">{prompt.question}</h3>
        <div className="flex flex-col gap-2">
          {prompt.options?.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => onRespond(idx + 1)}
              className={`
                flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm text-left
                transition-all duration-150
                ${idx + 1 === prompt.default
                  ? 'bg-accent/15 border border-accent/30 text-accent hover:bg-accent/25'
                  : 'bg-surface-200 border border-surface-300 text-text-primary hover:bg-surface-300'}
              `}
            >
              <span className="w-5 h-5 rounded-full bg-surface-300 flex items-center justify-center text-xs font-medium shrink-0">
                {idx + 1}
              </span>
              <span>{opt}</span>
              {idx + 1 === prompt.default && (
                <span className="ml-auto text-xs text-accent/60">recommended</span>
              )}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (prompt.type === 'confirm') {
    return (
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">{prompt.question}</h3>
        <div className="flex gap-3">
          <button
            onClick={() => onRespondConfirm(true)}
            className={`
              px-5 py-2 rounded-lg text-sm font-medium transition-all duration-150
              ${prompt.default === true
                ? 'bg-accent text-surface hover:bg-accent-hover'
                : 'bg-surface-200 text-text-primary hover:bg-surface-300 border border-surface-300'}
            `}
          >
            Yes
          </button>
          <button
            onClick={() => onRespondConfirm(false)}
            className={`
              px-5 py-2 rounded-lg text-sm font-medium transition-all duration-150
              ${prompt.default === false
                ? 'bg-accent text-surface hover:bg-accent-hover'
                : 'bg-surface-200 text-text-primary hover:bg-surface-300 border border-surface-300'}
            `}
          >
            No
          </button>
        </div>
      </div>
    );
  }

  if (prompt.type === 'path') {
    return (
      <div className="bg-surface-100 rounded-lg border border-surface-300 p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">{prompt.question}</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={pathValue}
            onChange={(e) => setPathValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && pathValue.trim()) {
                onRespond(pathValue.trim());
              }
            }}
            placeholder="Enter path..."
            className="flex-1 bg-surface-200 border border-surface-300 rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-accent/50"
            autoFocus
          />
          {onChooseDir && (
            <button
              onClick={async () => {
                const dir = await onChooseDir();
                if (dir) {
                  setPathValue(dir);
                  onRespond(dir);
                }
              }}
              className="px-3 py-2 rounded-lg bg-surface-200 border border-surface-300 text-text-secondary hover:text-text-primary hover:bg-surface-300 text-sm transition-colors"
            >
              Browse
            </button>
          )}
          <button
            onClick={() => {
              if (pathValue.trim()) onRespond(pathValue.trim());
            }}
            disabled={!pathValue.trim()}
            className="px-4 py-2 rounded-lg bg-accent text-surface text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    );
  }

  return null;
}
