
interface WelcomeStepProps {
  onStart: () => void;
  backendStatus: string;
  preflightStatus: 'idle' | 'checking' | 'ok' | 'missing';
  preflightMissing: string[];
  onRetryPreflight: () => void;
}

// Human-readable label + install URL for each missing component
const MISSING_INFO: Record<string, { label: string; url: string }> = {
  adb: {
    label: 'ADB (Android Debug Bridge) not found',
    url: 'https://developer.android.com/tools/releases/platform-tools',
  },
  sdk: {
    label: 'Android SDK not found',
    url: 'https://developer.android.com/studio',
  },
  python: {
    label: 'Python 3.8+ not found',
    url: 'https://www.python.org/downloads/',
  },
};

function PreflightBadge({
  preflightStatus,
  preflightMissing,
  onRetry,
}: {
  preflightStatus: WelcomeStepProps['preflightStatus'];
  preflightMissing: string[];
  onRetry: () => void;
}) {
  if (preflightStatus === 'idle') return null;

  if (preflightStatus === 'checking') {
    return (
      <div className="flex items-center gap-2 text-xs text-text-muted animate-pulse mb-6">
        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
        Checking environment…
      </div>
    );
  }

  if (preflightStatus === 'ok') {
    return (
      <div className="flex items-center gap-2 text-xs text-green-400 mb-6">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        Android SDK detected — ready to extract
      </div>
    );
  }

  // missing
  const openExternal = (url: string) => window.electronAPI?.shell.openExternal(url);
  const items = preflightMissing.length > 0 ? preflightMissing : ['sdk'];

  return (
    <div className="w-full max-w-md mb-6 rounded-xl border border-yellow-500/30 bg-yellow-500/8 p-4 text-left">
      <div className="flex items-start gap-3">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#facc15" strokeWidth="2" className="mt-0.5 shrink-0">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-yellow-300 mb-2">
            Missing prerequisites
          </p>
          <div className="flex flex-col gap-1.5 mb-3">
            {items.map((key) => {
              const info = MISSING_INFO[key] ?? { label: key, url: 'https://developer.android.com/studio' };
              return (
                <div key={key} className="flex items-center justify-between gap-3">
                  <span className="text-xs text-text-secondary">{info.label}</span>
                  <button
                    onClick={() => openExternal(info.url)}
                    className="shrink-0 text-xs text-accent hover:text-accent-hover underline"
                  >
                    Install →
                  </button>
                </div>
              );
            })}
          </div>
          <button
            onClick={onRetry}
            className="text-xs text-text-muted hover:text-text-primary transition-colors underline"
          >
            Re-check ↺
          </button>
        </div>
      </div>
    </div>
  );
}

export function WelcomeStep({
  onStart,
  backendStatus,
  preflightStatus,
  preflightMissing,
  onRetryPreflight,
}: WelcomeStepProps) {
  const isReady = backendStatus === 'connected' || backendStatus === 'starting';
  const isConnecting = backendStatus === 'starting' || backendStatus === 'disconnected';
  const canStart = isReady && preflightStatus !== 'missing';

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

      {/* Preflight / status area */}
      <PreflightBadge
        preflightStatus={preflightStatus}
        preflightMissing={preflightMissing}
        onRetry={onRetryPreflight}
      />

      {/* Backend status indicator — only shown while connecting */}
      {isConnecting && (
        <div className="flex items-center gap-2 mb-6">
          <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
          <span className="text-xs text-text-muted">Connecting to backend...</span>
        </div>
      )}

      <button
        onClick={onStart}
        disabled={!canStart}
        title={preflightStatus === 'missing' ? 'Fix environment issues first' : undefined}
        className="bg-accent text-surface font-medium px-8 py-2.5 rounded-lg hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 text-sm"
      >
        Begin Extraction
      </button>

      <div className="mt-10 flex gap-6 text-xs text-text-muted">
        <div className="flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          Secure &amp; local
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
