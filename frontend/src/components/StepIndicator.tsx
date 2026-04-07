import { Fragment } from 'react';
import { WIZARD_STEPS, WIZARD_LABELS, type WizardStep } from '../types';

interface StepIndicatorProps {
  currentStep: WizardStep;
  completedSteps: Set<WizardStep>;
}

export function StepIndicator({ currentStep, completedSteps }: StepIndicatorProps) {
  const currentIdx = WIZARD_STEPS.indexOf(currentStep);

  return (
    <div className="flex items-center gap-1 px-6 py-4">
      {WIZARD_STEPS.map((step, idx) => {
        const isActive = step === currentStep;
        const isCompleted = completedSteps.has(step);
        const isPast = idx < currentIdx;

        return (
          <Fragment key={step}>
            {idx > 0 && (
              <div
                className={`flex-1 h-px transition-colors duration-300 ${
                  isPast || isCompleted ? 'bg-accent' : 'bg-surface-300'
                }`}
              />
            )}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`
                  w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium
                  transition-all duration-300
                  ${isActive
                    ? 'bg-accent text-surface ring-2 ring-accent/30'
                    : isCompleted || isPast
                      ? 'bg-accent/20 text-accent'
                      : 'bg-surface-200 text-text-muted'}
                `}
              >
                {isCompleted || isPast ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  idx + 1
                )}
              </div>
              <span
                className={`text-[10px] font-medium tracking-wider uppercase whitespace-nowrap transition-colors duration-300 ${
                  isActive ? 'text-accent' : isPast || isCompleted ? 'text-text-secondary' : 'text-text-muted'
                }`}
              >
                {WIZARD_LABELS[step]}
              </span>
            </div>
          </Fragment>
        );
      })}
    </div>
  );
}
