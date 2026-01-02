import {
  BadRequestException,
  Inject,
  Injectable,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { setTimeout } from 'node:timers/promises';

import { NodeEnvEnum } from 'src/config/enum/node-env.enum';
import { SettingsStore } from 'src/settings/core/settings.store';
import {
  ClientTorrent,
  ClientTorrentFile,
  TorrentClient,
  TorrentClientToAddTorrent,
  TorrentClientToUpdateConfig,
} from 'src/torrents/ports/torrent-client.port';

import { LibTorrentClient, Torrent } from './client';
import { LIBTORRENT_CLIENT } from './libtorrent-client.token';
import { LibtorrentStreamService } from './libtorrent-stream.service';

@Injectable()
export class LibtorrentService implements TorrentClient {
  private readonly logger = new Logger(LibtorrentService.name);

  private readonly downloadsDir: string;
  private libtorrentEngineProcess: ReturnType<typeof spawn> | null = null;

  constructor(
    @Inject(LIBTORRENT_CLIENT)
    private readonly libtorrentClient: LibTorrentClient,
    private readonly libtorrentStreamService: LibtorrentStreamService,
    private readonly configService: ConfigService,
    private readonly settingsStore: SettingsStore,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
  }

  async bootstrap() {
    if (this.libtorrentEngineProcess) return;

    const port = this.configService.getOrThrow<number>('torrent.port');
    const peerLimit =
      this.configService.getOrThrow<number>('torrent.peer-limit');
    const nodeEnv = this.configService.getOrThrow<NodeEnvEnum>('app.node-env');

    const setting = await this.settingsStore.findOneOrThrow();

    const debugEnabled = nodeEnv === NodeEnvEnum.DEV;

    const repoRoot = join(process.cwd(), '../');
    const libtorrentEngineCwd = join(repoRoot, 'libtorrent-engine', 'src');
    const pythonPath = join(repoRoot, 'libtorrent-engine', 'src');

    const args: string[] = [];

    if (debugEnabled) {
      args.push('-m', 'debugpy', '--listen', `0.0.0.0:5678`);
    }

    args.push(
      '-m',
      'uvicorn',
      'main:app',
      '--port',
      '4300',
      '--log-config',
      '../logging.ini',
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
      this.logger.log(`[libtorrent engine] ${data.toString().trimEnd()}`);
    });

    this.libtorrentEngineProcess.stderr?.on('data', (data: Buffer) => {
      this.logger.error(`[libtorrent engine] ${data.toString().trimEnd()}`);
    });

    this.libtorrentEngineProcess.on('error', (err) => {
      this.logger.error(`spawn failed: ${err.message}`);
    });

    this.libtorrentEngineProcess.on('exit', (code, signal) => {
      this.logger.warn(`FastAPI leállt. code=${code} signal=${signal}`);
      this.libtorrentEngineProcess = null;
    });

    let started = false;

    while (!started) {
      try {
        await this.libtorrentClient.monitoring.health();
        started = true;
      } catch {
        await setTimeout(500);
      }
    }

    await this.libtorrentClient.torrents.updateSettings({
      port,
      download_rate_limit: setting.downloadLimit,
      upload_rate_limit: setting.uploadLimit,
      peer_limit: peerLimit,
    });

    this.logger.log('✅ libtorrent kliens elindult');
  }

  async shutdown() {
    if (!this.libtorrentEngineProcess) return;

    this.libtorrentEngineProcess.kill();
    this.libtorrentEngineProcess = null;

    let stopped = false;

    while (!stopped) {
      try {
        await this.libtorrentClient.monitoring.health();
        await setTimeout(500);
      } catch {
        stopped = true;
      }
    }

    this.logger.log('✅ libtorrent kliens leállítva.');
  }

  async updateConfig(payload: TorrentClientToUpdateConfig) {
    if (!this.libtorrentEngineProcess) return;

    await this.libtorrentClient.torrents.updateSettings({
      download_rate_limit: payload.downloadLimit,
      upload_rate_limit: payload.uploadLimit,
    });
  }

  async getTorrents(): Promise<ClientTorrent[]> {
    const torrents = await this.libtorrentClient.torrents.getTorrents();

    return torrents.map((torrent) => this.buildClientTorrent(torrent));
  }

  async getTorrent(infoHash: string): Promise<ClientTorrent | null> {
    try {
      const torrent = await this.libtorrentClient.torrents.getTorrent(infoHash);
      return this.buildClientTorrent(torrent);
    } catch {
      return null;
    }
  }

  async addTorrent(payload: TorrentClientToAddTorrent): Promise<ClientTorrent> {
    const torrent = await this.libtorrentClient.torrents.addTorrent({
      torrent_file_path: payload.torrentFilePath,
      save_path: this.downloadsDir,
      download_full_torrent: payload.downloadFullTorrent,
    });

    this.logger.log(
      `🎬 "${torrent.name}" nevű torrent hozzáadva a libtorrent-hez.`,
    );

    return this.buildClientTorrent(torrent);
  }

  async deleteTorrent(infoHash: string): Promise<ClientTorrent> {
    const torrent =
      await this.libtorrentClient.torrents.deleteTorrent(infoHash);

    this.logger.log(
      `🗑️ "${torrent.name}" nevű torrent törölve a libtorrent-ből.`,
    );

    return this.buildClientTorrent(torrent);
  }

  async getTorrentFile(
    infoHash: string,
    fileIndex: number,
  ): Promise<ClientTorrentFile> {
    const torrentFile = await this.libtorrentClient.torrents.getTorrentFile(
      infoHash,
      fileIndex,
    );

    return {
      infoHash: torrentFile.info_hash,
      fileIndex: torrentFile.file_index,
      name: torrentFile.path,
      total: torrentFile.size,
      createReadStream: async (ops) => {
        const file = await this.libtorrentClient.torrents.getTorrentFile(
          infoHash,
          fileIndex,
        );

        if (ops.start > ops.end) {
          throw new BadRequestException(
            `A "start" nem lehet nagyobb, mint az "end".`,
          );
        }

        if (ops.start >= file.size) {
          throw new BadRequestException(
            `A "start" nem lehet nagyobb vagy egyenlő, mint a "file.size".`,
          );
        }

        return this.libtorrentStreamService.createReadStream({
          infoHash,
          fileIndex,
          start: ops.start,
          end: ops.end,
          file: file,
        });
      },
    };
  }

  private buildClientTorrent(payload: Torrent): ClientTorrent {
    return {
      infoHash: payload.info_hash,
      name: payload.name,
      downloadSpeed: payload.download_speed,
      downloaded: payload.downloaded,
      uploadSpeed: payload.upload_speed,
      uploaded: payload.uploaded,
      progress: payload.progress,
      total: payload.total,
    };
  }
}
