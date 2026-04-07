import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private backendRoot: string;
  private rl: readline.Interface | null = null;

  constructor(backendRoot: string) {
    super();
    this.backendRoot = backendRoot;
  }

  private findPython(): { bin: string; args: string[] } {
    const isWin = process.platform === 'win32';

    // 1. Portable python in .python/
    const portableBin = isWin
      ? path.join(this.backendRoot, '.python', 'python.exe')
      : path.join(this.backendRoot, '.python', 'bin', 'python3');
    if (fs.existsSync(portableBin)) {
      return { bin: portableBin, args: [path.join(this.backendRoot, 'src', 'ipc_bridge.py')] };
    }

    // 2. venv-wvd
    const venvBin = isWin
      ? path.join(this.backendRoot, 'venv-wvd', 'Scripts', 'python.exe')
      : path.join(this.backendRoot, 'venv-wvd', 'bin', 'python3');
    if (fs.existsSync(venvBin)) {
      return { bin: venvBin, args: [path.join(this.backendRoot, 'src', 'ipc_bridge.py')] };
    }
    const venvBin2 = path.join(this.backendRoot, 'venv-wvd', 'bin', 'python');
    if (!isWin && fs.existsSync(venvBin2)) {
      return { bin: venvBin2, args: [path.join(this.backendRoot, 'src', 'ipc_bridge.py')] };
    }

    // 3. System fallback
    const fallback = isWin ? 'python' : 'python3';
    return { bin: fallback, args: [path.join(this.backendRoot, 'src', 'ipc_bridge.py')] };
  }

  start() {
    const { bin, args } = this.findPython();
    console.log(`[wvd:bridge] Starting backend: ${bin} ${args.join(' ')}`);
    console.log(`[wvd:bridge] Working dir: ${this.backendRoot}`);
    this.emit('status', 'starting');

    this.process = spawn(bin, args, {
      cwd: this.backendRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    if (!this.process.stdout || !this.process.stdin) {
      this.emit('error', 'Failed to spawn Python process');
      this.emit('status', 'disconnected');
      return;
    }

    this.rl = readline.createInterface({ input: this.process.stdout });

    this.rl.on('line', (line: string) => {
      try {
        const data = JSON.parse(line);
        console.log('[wvd:bridge] Event:', data.event || data.status || '');
        if (data.event === 'status' && data.status === 'ready') {
          this.emit('status', 'connected');
        }
        this.emit('event', data);
      } catch {
        console.log('[wvd:bridge] Non-JSON:', line);
      }
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) {
        console.error('[wvd:bridge] stderr:', msg);
      }
    });

    this.process.on('exit', (code) => {
      console.log(`[wvd:bridge] Process exited with code ${code}`);
      this.emit('status', 'disconnected');
    });

    this.process.on('error', (err) => {
      this.emit('status', 'disconnected');
      this.emit('error', `Failed to start Python: ${err.message}`);
    });
  }

  send(command: Record<string, unknown>) {
    if (this.process?.stdin?.writable) {
      console.log('[wvd:bridge] Sending:', JSON.stringify(command));
      this.process.stdin.write(JSON.stringify(command) + '\n');
    } else {
      console.error('[wvd:bridge] Cannot send — stdin not writable');
    }
  }

  stop() {
    this.rl?.close();
    this.rl = null;
    if (this.process) {
      this.send({ cmd: 'quit' });
      setTimeout(() => {
        this.process?.kill();
        this.process = null;
      }, 500);
    }
    this.emit('status', 'disconnected');
  }
}
