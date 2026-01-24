import { Inject, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosResponse } from 'axios';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { Readable } from 'node:stream';
import { setTimeout } from 'node:timers/promises';

import { NodeEnvEnum } from 'src/config/enum/node-env.enum';
import { RelaySettingsService } from 'src/settings/relay/relay-settings.service';
import {
  ClientTorrentFile,
  TorrentClientToAddTorrent,
  TorrentClientToUpdateConfig,
} from 'src/torrents/ports/torrent-client.port';

import { RelayClient, RelayTorrent } from './client';
import { RELAY_BASE_URL_PORT } from './relay.content';
import { RELAY_CLIENT } from './relay.token';
import { CreateReadStream } from './type/create-read-stream.type';

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

    const args: string[] = [];

    if (idDevEnv) {
      args.push('-m', 'debugpy', '--listen', `0.0.0.0:5678`);
    }

    const logConfig = idDevEnv ? '../logging.dev.ini' : '../logging.prod.ini';

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

    this.logger.log('✅ StremHU Relay elindult');
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

    this.logger.log('✅ libtorrent kliens leállítva.');
  }

  async updateConfig(payload: TorrentClientToUpdateConfig) {
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

  async addTorrent(payload: TorrentClientToAddTorrent): Promise<RelayTorrent> {
    const torrent = await this.relayClient.torrents.addTorrent({
      torrentFilePath: payload.torrentFilePath,
      savePath: this.downloadsDir,
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

    this.logger.log(
      `🎬 "${torrent.name}" nevű torrent hozzáadva a libtorrent-hez.`,
    );

    return torrent;
  }

  async deleteTorrent(infoHash: string): Promise<RelayTorrent> {
    const torrent = await this.relayClient.torrents.deleteTorrent(infoHash);

    this.logger.log(`🗑️ "${infoHash}" torrent törölve a libtorrent-ből.`);

    return torrent;
  }

  async getTorrentFile(
    infoHash: string,
    fileIndex: number,
  ): Promise<ClientTorrentFile> {
    const torrentFile = await this.relayClient.torrents.getTorrentFile(
      infoHash,
      fileIndex,
    );

    return {
      infoHash: torrentFile.infoHash,
      fileIndex: torrentFile.fileIndex,
      name: torrentFile.path,
      total: torrentFile.size,
    };
  }

  async playback(payload: CreateReadStream) {
    const controller = new AbortController();
    const response: AxiosResponse<Readable> = await axios.get(
      `http://127.0.0.1:4300/stream/${payload.infoHash}/${payload.fileIndex}`,
      {
        responseType: 'stream',
        headers: { Range: payload.range },
        signal: controller.signal,
      },
    );

    const stream = response.data;

    return { stream, controller };
  }

  private async restartEngine() {
    this.logger.warn(
      `[libtorrent] Újrainditas hiba miatt ${this.restartDelayMs}ms múlva.`,
    );

    await setTimeout(this.restartDelayMs);

    try {
      await this.bootstrap();
    } finally {
      this.isRestarting = false;
    }
  }
}
