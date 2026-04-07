
export function TitleBar() {
  const minimize = () => window.electronAPI?.window.minimize();
  const maximize = () => window.electronAPI?.window.maximize();
  const close = () => window.electronAPI?.window.close();

  return (
    <div className="drag-region flex items-center justify-between h-9 bg-surface-100 border-b border-surface-300 px-3 select-none shrink-0">
      <div className="flex items-center gap-2">
        <span className="text-accent font-semibold text-sm tracking-wide">WVD</span>
        <span className="text-text-secondary text-xs">Extractor</span>
      </div>
      <div className="no-drag flex items-center gap-1">
        <button
          onClick={minimize}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-200 text-text-secondary hover:text-text-primary transition-colors"
          aria-label="Minimize"
        >
          <svg width="10" height="1" viewBox="0 0 10 1"><rect fill="currentColor" width="10" height="1"/></svg>
        </button>
        <button
          onClick={maximize}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-200 text-text-secondary hover:text-text-primary transition-colors"
          aria-label="Maximize"
        >
          <svg width="10" height="10" viewBox="0 0 10 10"><rect fill="none" stroke="currentColor" strokeWidth="1" x="0.5" y="0.5" width="9" height="9"/></svg>
        </button>
        <button
          onClick={close}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-red-600 text-text-secondary hover:text-white transition-colors"
          aria-label="Close"
        >
          <svg width="10" height="10" viewBox="0 0 10 10"><line x1="0" y1="0" x2="10" y2="10" stroke="currentColor" strokeWidth="1.2"/><line x1="10" y1="0" x2="0" y2="10" stroke="currentColor" strokeWidth="1.2"/></svg>
        </button>
      </div>
    </div>
  );
}
