import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  BackendEvent,
  LogEntry,
  PendingPrompt,
  WizardStep,
} from '../types';

/**
 * Hook that manages the connection to the Python IPC backend.
 * Listens for backend events and provides a `send()` function.
 */
export function useBackend() {
  const [status, setStatus] = useState<string>('disconnected');
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(7);
  const [stepTitle, setStepTitle] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState<{ percent: number; label: string } | null>(null);
  const [prompt, setPrompt] = useState<PendingPrompt | null>(null);
  const [wvdPath, setWvdPath] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<string>('idle');
  const [preflightStatus, setPreflightStatus] = useState<'idle' | 'checking' | 'ok' | 'missing'>('idle');
  const [preflightMissing, setPreflightMissing] = useState<string[]>([]);
  const logIdRef = useRef(0);
  const preflightSentRef = useRef(false);

  const addLog = useCallback((type: LogEntry['type'], message: string) => {
    const id = ++logIdRef.current;
    setLogs(prev => [...prev, { id, type, message, timestamp: Date.now() }]);
  }, []);

  const send = useCallback((command: Record<string, unknown>) => {
    window.electronAPI?.python.send(command);
  }, []);

  useEffect(() => {
    const api = window.electronAPI;
    if (!api) return;

    const removeEvent = api.python.onEvent((raw) => {
      const data = raw as unknown as BackendEvent;
      if (!data.event) return;

      switch (data.event) {
        case 'step':
          setCurrentStep(data.step);
          setTotalSteps(data.total);
          setStepTitle(data.title);
          addLog('info', `[${data.step}/${data.total}] ${data.title}`);
          setProgress(null); // reset progress on new step
          break;

        case 'info':
          addLog('info', data.message);
          break;
        case 'success':
          addLog('success', data.message);
          break;
        case 'error':
          addLog('error', data.message);
          break;
        case 'warn':
          addLog('warn', data.message);
          break;
        case 'fatal':
          addLog('error', `FATAL: ${data.message}`);
          break;
        case 'log':
          addLog('log', data.message);
          break;

        case 'progress':
          setProgress({ percent: data.percent, label: data.label });
          break;

        case 'prompt_choice':
          setPrompt({
            type: 'choice',
            id: data.id,
            question: data.question,
            options: data.options,
            default: data.default,
          });
          break;
        case 'prompt_confirm':
          setPrompt({
            type: 'confirm',
            id: data.id,
            question: data.question,
            default: data.default,
          });
          break;
        case 'prompt_path':
          setPrompt({
            type: 'path',
            id: data.id,
            question: data.question,
          });
          break;

        case 'command_block': {
          const id = ++logIdRef.current;
          setLogs(prev => [...prev, {
            id,
            type: 'command',
            message: data.description || 'Run this command:',
            command: data.command,
            timestamp: Date.now(),
          }]);
          break;
        }

        case 'done':
          setWvdPath(data.wvd_path);          setPipelineStatus('finished');
          addLog('success', `Done! WVD file: ${data.wvd_path}`);
          break;

        case 'status':
          setPipelineStatus(data.status);
          break;

        case 'preflight_result':
          setPreflightStatus(data.ok ? 'ok' : 'missing');
          setPreflightMissing(data.missing ?? []);
          break;
      }
    });

    const removeStatus = api.python.onStatus((s) => {
      setStatus(s);
      // Trigger preflight automatically the first time the backend becomes ready.
      if (s === 'ready' && !preflightSentRef.current) {
        preflightSentRef.current = true;
        setPreflightStatus('checking');
        api.python.send({ cmd: 'preflight' });
      }
    });

    return () => {
      removeEvent();
      removeStatus();
    };
  }, [addLog]);

  const respondToPrompt = useCallback((value: unknown) => {
    send({ cmd: 'respond', value });
    setPrompt(null);
  }, [send]);

  const respondConfirm = useCallback((value: boolean) => {
    send({ cmd: 'respond', value });
    setPrompt(null);
  }, [send]);

  const retryPreflight = useCallback(() => {
    setPreflightStatus('checking');
    send({ cmd: 'preflight' });
  }, [send]);

  const clearLogs = useCallback(() => {
    setLogs([]);
    logIdRef.current = 0;
  }, []);

  return {
    status,
    currentStep,
    totalSteps,
    stepTitle,
    logs,
    progress,
    prompt,
    wvdPath,
    pipelineStatus,
    preflightStatus,
    preflightMissing,
    send,
    respondToPrompt,
    respondConfirm,
    retryPreflight,
    addLog,
    clearLogs,
  };
}

/**
 * Hook that manages the wizard step navigation.
 * The wizard auto-advances based on backend step numbers.
 */
export function useWizard(backendStep: number, pipelineStatus: string) {
  const [wizardStep, setWizardStep] = useState<WizardStep>('welcome');
  const [started, setStarted] = useState(false);

  // Map backend steps (1-7) to wizard steps
  useEffect(() => {
    if (!started) return;

    if (pipelineStatus === 'finished') {
      setWizardStep('done');
      return;
    }
    if (pipelineStatus === 'error') {
      // Stay on current step to show error
      return;
    }

    if (backendStep >= 7) {
      setWizardStep('install');
    } else if (backendStep >= 4) {
      setWizardStep('extraction');
    } else if (backendStep >= 3) {
      setWizardStep('device');
    } else if (backendStep >= 1) {
      setWizardStep('environment');
    }
  }, [backendStep, pipelineStatus, started]);

  const goTo = useCallback((step: WizardStep) => {
    setWizardStep(step);
  }, []);

  const markStarted = useCallback(() => {
    setStarted(true);
    setWizardStep('environment');
  }, []);

  return {
    wizardStep,
    started,
    goTo,
    markStarted,
  };
}
