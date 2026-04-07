
interface DoneStepProps {
  wvdPath: string | null;
  onOpenFolder: () => void;
  onClose: () => void;
}

export function DoneStep({ wvdPath, onOpenFolder, onClose }: DoneStepProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      {/* Success icon */}
      <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mb-6">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="text-green-400">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M8 12l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>

      <h1 className="text-2xl font-semibold text-text-primary mb-2">
        Extraction Complete!
      </h1>
      <p className="text-sm text-text-secondary max-w-md mb-2">
        Your Widevine Client Device Module has been successfully extracted and saved.
      </p>

      {wvdPath && (
        <div className="bg-surface-100 rounded-lg border border-surface-300 px-4 py-3 mb-6 max-w-lg">
          <div className="flex items-center gap-3">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-accent shrink-0">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="1.5"/>
              <polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span className="text-xs text-text-secondary break-all text-left">{wvdPath}</span>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        {wvdPath && (
          <button
            onClick={onOpenFolder}
            className="bg-surface-200 text-text-primary font-medium px-5 py-2.5 rounded-lg hover:bg-surface-300 border border-surface-300 transition-all duration-150 text-sm"
          >
            Open Folder
          </button>
        )}
        <button
          onClick={onClose}
          className="bg-accent text-surface font-medium px-8 py-2.5 rounded-lg hover:bg-accent-hover transition-all duration-150 text-sm"
        >
          Close
        </button>
      </div>

      <p className="text-xs text-text-muted mt-8 max-w-sm">
        You can now use this WVD file with Cesio-138 or any tool that supports Widevine CDM modules.
      </p>
    </div>
  );
}
