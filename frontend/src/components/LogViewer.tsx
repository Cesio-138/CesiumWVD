import { useEffect, useRef, useState } from 'react';
import type { LogEntry } from '../types';

interface LogViewerProps {
  logs: LogEntry[];
  maxHeight?: string;
}

const TYPE_COLORS: Record<LogEntry['type'], string> = {
  info: 'text-text-secondary',
  success: 'text-green-400',
  error: 'text-red-400',
  warn: 'text-yellow-400',
  log: 'text-text-muted',
  command: '',
};

const TYPE_ICONS: Record<LogEntry['type'], string> = {
  info: '→',
  success: '✓',
  error: '✗',
  warn: '⚠',
  log: ' ',
  command: '',
};

function CommandBlock({ entry }: { entry: LogEntry }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!entry.command) return;
    navigator.clipboard.writeText(entry.command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleOpenAdmin = () => {
    if (!entry.command) return;
    window.electronAPI?.shell.openPowerShellAdmin(entry.command);
  };

  return (
    <div className="my-2 rounded-lg border border-cyan-500/40 bg-black/40 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-cyan-500/10 border-b border-cyan-500/30">
        <span className="text-xs text-cyan-400 font-semibold uppercase tracking-wide">
          {entry.message}
        </span>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="text-xs px-2 py-0.5 rounded bg-surface-300 hover:bg-surface-400 text-text-secondary transition-colors"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
          <button
            onClick={handleOpenAdmin}
            className="text-xs px-2 py-0.5 rounded bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 transition-colors"
            title="Open PowerShell as Administrator and run this command"
          >
            Open as Admin ↗
          </button>
        </div>
      </div>
      <pre className="px-4 py-3 text-sm text-cyan-100 font-mono whitespace-pre-wrap break-all">
        {entry.command}
      </pre>
    </div>
  );
}

export function LogViewer({ logs, maxHeight = '200px' }: LogViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [logsCopied, setLogsCopied] = useState(false);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  if (logs.length === 0) return null;

  const handleCopyLogs = () => {
    const text = logs
      .map(e => e.type === 'command' ? `$ ${e.command ?? e.message}` : `${TYPE_ICONS[e.type]} ${e.message}`)
      .join('\n');
    navigator.clipboard.writeText(text).then(() => {
      setLogsCopied(true);
      setTimeout(() => setLogsCopied(false), 2000);
    });
  };

  return (
    <div>
      <div
        ref={containerRef}
        className="log-container bg-surface rounded-lg border border-surface-300 border-b-0 rounded-b-none p-3 overflow-y-auto"
        style={{ maxHeight }}
      >
        {logs.map((entry) =>
          entry.type === 'command' ? (
            <CommandBlock key={entry.id} entry={entry} />
          ) : (
            <div key={entry.id} className={`flex gap-2 ${TYPE_COLORS[entry.type]}`}>
              <span className="shrink-0 w-3 text-center">{TYPE_ICONS[entry.type]}</span>
              <span className="break-all whitespace-pre-wrap">{entry.message}</span>
            </div>
          )
        )}
      </div>
      <div className="flex justify-end bg-surface-100 rounded-b-lg border border-surface-300 border-t-0 px-3 py-1">
        <button
          onClick={handleCopyLogs}
          className="text-[10px] text-text-muted hover:text-text-secondary transition-colors"
        >
          {logsCopied ? '✓ Copied' : 'Copy log'}
        </button>
      </div>
    </div>
  );
}
