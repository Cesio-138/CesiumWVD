
interface WelcomeStepProps {
  onStart: () => void;
  backendStatus: string;
}

export function WelcomeStep({ onStart, backendStatus }: WelcomeStepProps) {
  const isReady = backendStatus === 'connected' || backendStatus === 'starting';
  const isConnecting = backendStatus === 'starting' || backendStatus === 'disconnected';

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      {/* Logo / Icon */}
      <div className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center mb-6">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="text-accent">
          <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <path d="M12 22V12" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M22 7l-10 5-10-5" stroke="currentColor" strokeWidth="1.5"/>
          <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.4"/>
        </svg>
      </div>

      <h1 className="text-2xl font-semibold text-text-primary mb-2">
        WVD Extractor
      </h1>
      <p className="text-sm text-text-secondary max-w-md mb-2">
        Extract a Widevine Client Device Module (WVD) from an Android device or emulator.
        This wizard will guide you through every step.
      </p>
      <p className="text-xs text-text-muted max-w-sm mb-8">
        Requires Android SDK with an emulator or a connected device with root access.
        The process takes about 3-5 minutes.
      </p>

      {/* Status indicator */}
      <div className="flex items-center gap-2 mb-6">
        <div className={`w-2 h-2 rounded-full ${isConnecting ? 'bg-yellow-400 animate-pulse' : isReady ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-xs text-text-muted">
          {isConnecting ? 'Connecting to backend...' : isReady ? 'Backend ready' : 'Backend disconnected'}
        </span>
      </div>

      <button
        onClick={onStart}
        disabled={!isReady && !isConnecting}
        className="bg-accent text-surface font-medium px-8 py-2.5 rounded-lg hover:bg-accent-hover disabled:opacity-40 transition-all duration-150 text-sm"
      >
        Begin Extraction
      </button>

      <div className="mt-10 flex gap-6 text-xs text-text-muted">
        <div className="flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          Secure & local
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          ~3-5 minutes
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          Fully guided
        </div>
      </div>
    </div>
  );
}
