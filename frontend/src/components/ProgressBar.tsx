
interface ProgressBarProps {
  percent: number | null;
  label?: string;
  indeterminate?: boolean;
}

export function ProgressBar({ percent, label, indeterminate }: ProgressBarProps) {
  return (
    <div className="w-full">
      {label && (
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-text-secondary">{label}</span>
          {percent !== null && !indeterminate && (
            <span className="text-xs text-text-muted">{percent}%</span>
          )}
        </div>
      )}
      <div className="w-full h-1 bg-surface-300 rounded-full overflow-hidden">
        {indeterminate ? (
          <div className="w-1/4 h-full bg-accent rounded-full progress-indeterminate" />
        ) : (
          <div
            className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
            style={{ width: `${Math.min(100, percent ?? 0)}%` }}
          />
        )}
      </div>
    </div>
  );
}
