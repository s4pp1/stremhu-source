import {
  Injectable,
  InternalServerErrorException,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import { Readable } from 'node:stream';
import { Torrent } from 'webtorrent';

import { SettingsStore } from 'src/settings/core/settings.store';
import {
  ClientTorrent,
  ClientTorrentFile,
  TorrentClient,
  TorrentClientToAddTorrent,
  TorrentClientToUpdateConfig,
} from 'src/torrents/ports/torrent-client.port';

@Injectable()
export class WebTorrentService implements TorrentClient {
  private readonly logger = new Logger(WebTorrentService.name);

  private readonly downloadsDir: string;
  private readonly storeCacheSlots: number;

  private client: import('webtorrent').Instance | undefined;

  constructor(
    private readonly configService: ConfigService,
    private readonly settingsStore: SettingsStore,
  ) {
    this.downloadsDir = this.configService.getOrThrow<string>(
      'torrent.downloads-dir',
    );
    this.storeCacheSlots = this.configService.getOrThrow<number>(
      'torrent.store-cache-slots',
    );
  }

  async bootstrap() {
    const setting = await this.settingsStore.findOneOrThrow();
    const torrentPort = this.configService.getOrThrow<number>('torrent.port');
    const maxConns =
      this.configService.getOrThrow<number>('torrent.peer-limit');

    const { default: WebTorrent } = await import('webtorrent');

    this.client = new WebTorrent({
      utp: false,
      dht: false,
      webSeeds: false,
      lsd: false,
      torrentPort,
      maxConns,
      downloadLimit: setting.downloadLimit,
      uploadLimit: setting.uploadLimit,
    });

    this.logger.log('✅ WebTorrent kliens elindult');

    this.client.on('error', (err) => {
      this.logger.error('⚠️ WebTorrent hiba:', err);
    });
  }

  async shutdown() {
    const webtorrent = this.getClient();

    await new Promise<void>((resolve) => {
      webtorrent.destroy(() => {
        this.logger.log('✅ WebTorrent kliens leállítva.');
        resolve();
      });
    });
  }

  updateConfig(payload: TorrentClientToUpdateConfig) {
    const webtorrent = this.getClient();

    webtorrent.throttleDownload(payload.downloadLimit);
    webtorrent.throttleUpload(payload.uploadLimit);
  }

  getTorrents(): ClientTorrent[] {
    const webtorrent = this.getClient();

    return webtorrent.torrents.map((torrent) =>
      this.buildClientTorrent(torrent),
    );
  }

  async getTorrent(infoHash: string): Promise<ClientTorrent | null> {
    const webtorrent = this.getClient();

    const torrent = await webtorrent.get(infoHash);

    if (!torrent) {
      return null;
    }

    return this.buildClientTorrent(torrent);
  }

  addTorrent(payload: TorrentClientToAddTorrent): Promise<ClientTorrent> {
    const webtorrent = this.getClient();

    return new Promise((resolve, reject) => {
      const { torrentFilePath, downloadFullTorrent = false } = payload;

      const torrent = webtorrent.add(
        torrentFilePath,
        {
          path: this.downloadsDir,
          storeCacheSlots: this.storeCacheSlots,
          deselect: !downloadFullTorrent,
        },
        (torrent) => {
          this.logger.log(
            `🎬 "${torrent.name}" nevű torrent hozzáadva a WebTorrent-hez.`,
          );

          resolve(this.buildClientTorrent(torrent));
        },
      );

      torrent.once('error', reject);
    });
  }

  async deleteTorrent(infoHash: string): Promise<ClientTorrent> {
    const webtorrent = this.getClient();

    const torrent = await webtorrent.get(infoHash);

    if (!torrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem létezik.`);
    }

    await webtorrent.remove(torrent.infoHash, { destroyStore: true });

    const torrentPath = join(torrent.path, torrent.name);
    await rm(torrentPath, { recursive: true, force: true });

    this.logger.log(
      `🗑️ "${torrent.name}" nevű torrent törölve a WebTorrent-ből.`,
    );

    return this.buildClientTorrent(torrent);
  }

  async getTorrentFile(
    infoHash: string,
    fileIndex: number,
  ): Promise<ClientTorrentFile> {
    const webtorrent = this.getClient();

    const torrent = await webtorrent.get(infoHash);

    if (!torrent) {
      throw new NotFoundException();
    }

    const torrentFile = torrent.files[fileIndex];

    if (!torrentFile) {
      throw new NotFoundException();
    }

    return {
      infoHash: torrent.infoHash,
      fileIndex: fileIndex,
      name: torrentFile.name,
      total: torrentFile.length,
      createReadStream: (ops) => torrentFile.createReadStream(ops) as Readable,
    };
  }

  private getClient() {
    if (!this.client) {
      throw new InternalServerErrorException();
    }

    return this.client;
  }

  private buildClientTorrent(payload: Torrent): ClientTorrent {
    return {
      infoHash: payload.infoHash,
      name: payload.name,
      downloadSpeed: payload.downloadSpeed,
      downloaded: payload.downloaded,
      uploadSpeed: payload.uploadSpeed,
      uploaded: payload.uploaded,
      progress: payload.progress,
      total: payload.length,
    };
  }
}
