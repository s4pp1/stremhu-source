import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { setTimeout } from 'node:timers/promises';

import { NodeEnvEnum } from 'src/config/enum/node-env.enum';
import { RelaySettingsService } from 'src/settings/relay/relay-settings.service';

import { RelayClient, RelayTorrent, UpdateSettings } from './client';
import { RELAY_BASE_URL_PORT } from './relay.content';
import { RELAY_CLIENT } from './relay.token';
import { AddRelayTorrent } from './type/add-relay-torrent.type';

@Injectable()
export class RelayService {
  private readonly logger = new Logger(RelayService.name);

  private readonly downloadsDir: string;
  private libtorrentEngineProcess: ReturnType<typeof spawn> | null = null;
  private isShuttingDown = false;
  private isRestarting = false;
  private readonly restartDelayMs = 1000;

  constructor(
    @Inject(RELAY_CLIENT)
    private readonly relayClient: RelayClient,
    private readonly configService: ConfigService,
    private readonly relaySettingsService: RelaySettingsService,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  async bootstrap() {
    if (this.libtorrentEngineProcess) return;

    this.isShuttingDown = false;

    const port = this.configService.getOrThrow<number>('torrent.port');
    const nodeEnv = this.configService.getOrThrow<NodeEnvEnum>('app.node-env');

    const setting = await this.relaySettingsService.get();

    const idDevEnv = nodeEnv === NodeEnvEnum.DEV;

    const repoRoot = join(process.cwd(), '../');
    const libtorrentEngineCwd = join(repoRoot, 'relay', 'src');
    const pythonPath = join(repoRoot, 'relay', 'src');

    let logConfig = '../logging.prod.ini';

    const args: string[] = [];

    if (idDevEnv) {
      logConfig = '../logging.dev.ini';
      args.push('-m', 'debugpy', '--listen', `0.0.0.0:5678`);
    }

    args.push(
      '-m',
      'uvicorn',
      'main:app',
      '--port',
      RELAY_BASE_URL_PORT,
      '--log-config',
      logConfig,
    );

    this.libtorrentEngineProcess = spawn('python', args, {
      cwd: libtorrentEngineCwd,
      env: {
        ...process.env,
        PYTHONPATH: pythonPath,
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
      this.logger.warn(`[Relay] FastAPI leállt. code=${code} signal=${signal}`);
      this.libtorrentEngineProcess = null;

      if (this.isShuttingDown) return;

      const isErrorExit = (code !== null && code !== 0) || signal !== null;

      if (!isErrorExit || this.isRestarting) return;

      this.isRestarting = true;
      void this.restartEngine();
    });

    let started = false;

    while (!started) {
      try {
        await this.relayClient.monitoring.health();
        started = true;
      } catch {
        await setTimeout(500);
      }
    }

    await this.updateConfig({ ...setting, port });

    this.logger.log('✅ StremHU Relay (libtorrent) elindult');
  }

  async shutdown() {
    if (!this.libtorrentEngineProcess) return;

    this.isShuttingDown = true;
    this.libtorrentEngineProcess.kill();
    this.libtorrentEngineProcess = null;

    let stopped = false;

    while (!stopped) {
      try {
        await this.relayClient.monitoring.health();
        await setTimeout(500);
      } catch {
        stopped = true;
      }
    }

    this.logger.log('✅ StremHU Relay (libtorrent) leállítva.');
  }

  async updateConfig(payload: UpdateSettings) {
    if (!this.libtorrentEngineProcess) return;

    await this.relayClient.setting.update(payload);
  }

  async getTorrents(): Promise<RelayTorrent[]> {
    const torrents = await this.relayClient.torrents.getTorrents();
    return torrents;
  }

  async getTorrent(infoHash: string): Promise<RelayTorrent | null> {
    try {
      const torrent = await this.relayClient.torrents.getTorrent(infoHash);
      return torrent;
    } catch {
      return null;
    }
  }

  async addTorrent(payload: AddRelayTorrent): Promise<RelayTorrent> {
    const torrent = await this.relayClient.torrents.addTorrent({
      savePath: this.downloadsDir,
      torrentFilePath: payload.torrentFilePath,
      downloadFullTorrent: payload.downloadFullTorrent,
    });

    let isChecking = [1, 2, 7].includes(torrent.state);

    while (isChecking) {
      const { state, progress } =
        await this.relayClient.torrents.getTorrentState(torrent.infoHash);

      isChecking = [1, 2, 7].includes(state);
      if (isChecking) {
        const percentage = progress * 100;
        this.logger.log(
          `⏳ A(z) "${torrent.name}" torrent ellenörzés alatt van: ${percentage.toPrecision(2)}%`,
        );
      }
      await setTimeout(2000);
    }

    this.logger.log(`🎬 "${torrent.name}" nevű torrent hozzáadva a Relay-hez.`);

    return torrent;
  }

  async deleteTorrent(infoHash: string): Promise<RelayTorrent> {
    const torrent = await this.relayClient.torrents.deleteTorrent(infoHash);

    this.logger.log(`🗑️ "${infoHash}" torrent törölve a Relay-ből.`);

    return torrent;
  }

  private async restartEngine() {
    this.logger.warn(
      `[Relay] Újrainditas hiba miatt ${this.restartDelayMs}ms múlva.`,
    );

    await setTimeout(this.restartDelayMs);

    try {
      await this.bootstrap();
    } finally {
      this.isRestarting = false;
    }
  }
}
