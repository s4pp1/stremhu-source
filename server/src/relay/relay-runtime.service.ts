import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { BehaviorSubject, firstValueFrom } from 'rxjs';
import { filter } from 'rxjs/operators';

import { RelayClient } from './client';
import {
  HEARTBEAT_INTERVAL_MS,
  MAX_RESTARTS,
  RELAY_BASE_URL_PORT,
  RESTART_DELAY_MS,
} from './relay.constant';
import { RELAY_CLIENT } from './relay.token';
import { RelayStatus } from './type/relay-status.enum';

@Injectable()
export class RelayRuntimeService {
  private readonly logger = new Logger(RelayRuntimeService.name);

  private libtorrentEngineProcess: ReturnType<typeof spawn> | null = null;
  private isShuttingDown = false;
  private isHeartbeating = false;
  private restartCount = 0;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lastRelayStartTime: number | null = null;
  private autoStart = false;

  private readonly status$ = new BehaviorSubject<RelayStatus>(
    RelayStatus.INITIALIZING,
  );

  constructor(
    @Inject(RELAY_CLIENT)
    private readonly relayClient: RelayClient,
    private readonly configService: ConfigService,
  ) {
    this.autoStart = this.configService.getOrThrow<boolean>(
      'torrent.relay-auto-start',
    );
  }

  async bootstrap() {
    if (this.libtorrentEngineProcess) return;

    this.isShuttingDown = false;
    this.status$.next(RelayStatus.INITIALIZING);

    if (this.autoStart) {
      const repoRoot = join(process.cwd(), '../');
      const relayPath = join(repoRoot, 'relay', 'src');

      const args: string[] = [
        '-m',
        'uvicorn',
        'main:app',
        '--port',
        RELAY_BASE_URL_PORT,
        '--log-config',
        '../logging.ini',
      ];

      this.libtorrentEngineProcess = spawn('python', args, {
        cwd: relayPath,
        env: {
          ...process.env,
          PYTHONPATH: relayPath,
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      this.libtorrentEngineProcess.stdout?.on('data', (data: Buffer) => {
        this.logger.log(`[Relay] ${data.toString().trimEnd()}`);
      });

      this.libtorrentEngineProcess.stderr?.on('data', (data: Buffer) => {
        this.logger.error(`[Relay] ${data.toString().trimEnd()}`);
      });

      this.libtorrentEngineProcess.on('error', (err) => {
        this.logger.error(`[Relay] Nem sikerült elindítani: ${err.message}`);
      });

      this.libtorrentEngineProcess.on('exit', (code, signal) => {
        this.logger.warn(
          `[Relay] FastAPI leállt. code=${code} signal=${signal}`,
        );
        this.libtorrentEngineProcess = null;

        if (this.isShuttingDown) return;

        const isErrorExit = (code !== null && code !== 0) || signal !== null;

        if (!isErrorExit) return;

        void this.restartEngine();
      });
    } else {
      this.logger.log(
        'ℹ️ [Relay] Manuális indítási mód. Várakozás a külső Relay-re...',
      );
    }

    let started = false;

    while (!started) {
      try {
        const health = await this.relayClient.monitoring.health();
        this.lastRelayStartTime = health.startTime;

        started = true;
      } catch {
        await sleep(1000);
      }
    }

    this.status$.next(RelayStatus.ONLINE);

    this.restartCount = 0;

    this.startHeartbeat();
  }

  async shutdown() {
    this.stopHeartbeat();
    if (!this.libtorrentEngineProcess) return;

    this.isShuttingDown = true;
    this.status$.next(RelayStatus.OFFLINE);

    this.libtorrentEngineProcess.kill();

    await new Promise((resolve) => {
      this.libtorrentEngineProcess!.on('exit', () => resolve(true));
      this.libtorrentEngineProcess!.on('close', () => resolve(true));

      setTimeout(() => resolve(true), 5000);
    });

    this.libtorrentEngineProcess = null;
  }

  getStatus$() {
    return this.status$.asObservable();
  }

  private async restartEngine() {
    if (!this.autoStart) {
      this.status$.next(RelayStatus.OFFLINE);
      this.logger.warn(
        `Relay leállt vagy nem elérhető. Kérlek indítsd el manuálisan!`,
      );
      return;
    }

    if (this.restartCount >= MAX_RESTARTS) {
      this.status$.next(RelayStatus.CRITICAL_ERROR);
      this.logger.error(
        `🚨 Relay elérte az újraindítási limitet (${MAX_RESTARTS}). Az alkalmazás leáll.`,
      );
      process.exit(1);
    }

    this.restartCount++;
    this.status$.next(RelayStatus.RESTARTING);
    this.logger.warn(
      `Relay újraindítása hiba miatt ${RESTART_DELAY_MS}ms múlva.`,
    );

    await sleep(RESTART_DELAY_MS);

    try {
      await this.bootstrap();
    } catch (err) {
      this.logger.error(`Relay sikertelen újraindítás.`, err);
      void this.restartEngine();
    }
  }

  private async waitUntilOnline(): Promise<void> {
    if (this.status$.value === RelayStatus.ONLINE) return;

    this.logger.log('⏳ Várakozás a Relay-re...');
    await firstValueFrom(
      this.status$.pipe(filter((status) => status === RelayStatus.ONLINE)),
    );
  }

  public async request<T>(fn: () => Promise<T>): Promise<T> {
    await this.waitUntilOnline();
    try {
      return await fn();
    } catch (err) {
      if (this.isShuttingDown) throw err;

      if (axios.isAxiosError(err)) {
        const isConnectionError = err.code === 'ECONNREFUSED';

        if (isConnectionError) {
          this.logger.warn('Relay API kapcsolódási hiba. Újrapróbálkozás...');
          this.status$.next(RelayStatus.OFFLINE);
          return this.request(fn);
        }
      }

      throw err;
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      void this.runHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);

    void this.runHeartbeat();
  }

  private async runHeartbeat() {
    if (this.isShuttingDown || this.isHeartbeating) return;

    this.isHeartbeating = true;

    try {
      const response = await this.relayClient.monitoring.health();
      const currentStartTime = response.startTime;

      if (
        this.lastRelayStartTime !== null &&
        currentStartTime !== this.lastRelayStartTime
      ) {
        this.logger.warn(
          'Relay újraindulás detektálva. Szinkronizáció kényszerítése...',
        );
        this.status$.next(RelayStatus.OFFLINE);
        this.status$.next(RelayStatus.ONLINE);
      }

      this.lastRelayStartTime = currentStartTime;

      if (this.status$.value !== RelayStatus.ONLINE) {
        this.status$.next(RelayStatus.ONLINE);
        this.logger.log('✅ Relay újra elérhető');
      }
    } catch (err) {
      this.logger.error(`🚨 Relay nem érhető el, újraindítás...`, err);
      this.status$.next(RelayStatus.OFFLINE);

      if (this.autoStart) {
        this.stopHeartbeat();

        if (this.libtorrentEngineProcess) {
          this.libtorrentEngineProcess.kill();
        } else {
          await this.restartEngine();
        }
      }
    } finally {
      this.isHeartbeating = false;
    }
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}
