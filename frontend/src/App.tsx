import { useMemo, useCallback } from 'react';
import { TitleBar } from './components/TitleBar';
import { StepIndicator } from './components/StepIndicator';
import { WelcomeStep } from './components/steps/WelcomeStep';
import { EnvironmentStep } from './components/steps/EnvironmentStep';
import { DeviceStep } from './components/steps/DeviceStep';
import { ExtractionStep } from './components/steps/ExtractionStep';
import { InstallStep } from './components/steps/InstallStep';
import { DoneStep } from './components/steps/DoneStep';
import { useBackend, useWizard } from './hooks/useBackend';
import type { WizardStep, LogEntry } from './types';
import { WIZARD_STEPS } from './types';

export default function App() {
  const backend = useBackend();
  const wizard = useWizard(backend.currentStep, backend.pipelineStatus);

  const handleStart = useCallback(() => {
    wizard.markStarted();
    backend.clearLogs();
    backend.send({ cmd: 'start', options: { timeout: 180 } });
  }, [wizard, backend]);

  const handleRetry = useCallback(() => {
    backend.clearLogs();
    backend.send({ cmd: 'start', options: { timeout: 180 } });
  }, [backend]);

  const handleOpenFolder = useCallback(() => {
    if (backend.wvdPath) {
      // Open the parent directory
      const dir = backend.wvdPath.substring(0, backend.wvdPath.lastIndexOf('/'));
      window.electronAPI?.shell.openPath(dir || backend.wvdPath);
    }
  }, [backend.wvdPath]);

  const handleClose = useCallback(() => {
    window.electronAPI?.window.close();
  }, []);

  const handleChooseDir = useCallback(async () => {
    return window.electronAPI?.dialog.chooseDir() ?? null;
  }, []);

  // Compute completed steps for the indicator
  const completedSteps = useMemo(() => {
    const completed = new Set<WizardStep>();
    const currentIdx = WIZARD_STEPS.indexOf(wizard.wizardStep);
    for (let i = 0; i < currentIdx; i++) {
      completed.add(WIZARD_STEPS[i]);
    }
    if (backend.pipelineStatus === 'finished') {
      WIZARD_STEPS.forEach(s => completed.add(s));
    }
    return completed;
  }, [wizard.wizardStep, backend.pipelineStatus]);

  // Filter logs relevant to current wizard step
  const filteredLogs = useMemo(() => {
    // For simplicity, show all logs accumulated so far
    // The LogViewer auto-scrolls to bottom anyway
    return backend.logs;
  }, [backend.logs]);

  // Get logs for a specific step range
  const getStepLogs = useCallback((_fromStep: number, _toStep: number): LogEntry[] => {
    // We track logs globally; filter based on when steps changed
    // For simplicity, just return all logs — they auto-scroll
    return filteredLogs;
  }, [filteredLogs]);

  return (
    <div className="flex flex-col h-screen bg-surface select-none">
      <TitleBar />

      {/* Step indicator — shown once the wizard has started */}
      {wizard.started && wizard.wizardStep !== 'done' && (
        <StepIndicator currentStep={wizard.wizardStep} completedSteps={completedSteps} />
      )}

      {/* Main content area */}
      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4">
        <div className="step-active h-full">
          {wizard.wizardStep === 'welcome' && (
            <WelcomeStep
              onStart={handleStart}
              backendStatus={backend.status}
            />
          )}
          {wizard.wizardStep === 'environment' && (
            <EnvironmentStep
              logs={getStepLogs(1, 2)}
              progress={backend.progress}
              pipelineStatus={backend.pipelineStatus}
              onRetry={handleRetry}
            />
          )}
          {wizard.wizardStep === 'device' && (
            <DeviceStep
              logs={getStepLogs(3, 3)}
              progress={backend.progress}
              prompt={backend.prompt}
              onRespond={backend.respondToPrompt}
              onRespondConfirm={backend.respondConfirm}
              pipelineStatus={backend.pipelineStatus}
              onRetry={handleRetry}
            />
          )}
          {wizard.wizardStep === 'extraction' && (
            <ExtractionStep
              logs={getStepLogs(4, 6)}
              progress={backend.progress}
              backendStep={backend.currentStep}
              pipelineStatus={backend.pipelineStatus}
              onRetry={handleRetry}
            />
          )}
          {wizard.wizardStep === 'install' && (
            <InstallStep
              logs={getStepLogs(7, 7)}
              prompt={backend.prompt}
              onRespond={backend.respondToPrompt}
              onRespondConfirm={backend.respondConfirm}
              onChooseDir={handleChooseDir}
            />
          )}
          {wizard.wizardStep === 'done' && (
            <DoneStep
              wvdPath={backend.wvdPath}
              onOpenFolder={handleOpenFolder}
              onClose={handleClose}
            />
          )}
        </div>
      </div>

      {/* Bottom status bar */}
      <div className="h-7 bg-surface-100 border-t border-surface-300 px-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${
            backend.status === 'connected' ? 'bg-green-400' :
            backend.status === 'starting' ? 'bg-yellow-400 animate-pulse' :
            'bg-red-400'
          }`} />
          <span className="text-[10px] text-text-muted">
            {backend.status === 'connected' ? 'Backend connected' :
             backend.status === 'starting' ? 'Starting...' :
             'Disconnected'}
          </span>
        </div>
        {backend.currentStep > 0 && backend.pipelineStatus === 'running' && (
          <span className="text-[10px] text-text-muted">
            Step {backend.currentStep}/{backend.totalSteps}: {backend.stepTitle}
          </span>
        )}
      </div>
    </div>
  );
}
