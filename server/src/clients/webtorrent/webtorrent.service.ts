import {
  Injectable,
  InternalServerErrorException,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { SettingsStore } from 'src/settings/core/settings.store';
import {
  TorrentClient,
  TorrentClientToAddTorrent,
  TorrentClientToUpdateConfig,
} from 'src/torrents/ports/torrent-client.port';

import type { WebTorrentTorrent } from './webtorrent.types';

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
      'web-torrent.downloads-dir',
    );
    this.storeCacheSlots = this.configService.getOrThrow<number>(
      'web-torrent.store-cache-slots',
    );
  }

  async bootstrap() {
    const setting = await this.settingsStore.findOneOrThrow();
    const torrentPort =
      this.configService.getOrThrow<number>('web-torrent.port');
    const maxConns = this.configService.getOrThrow<number>(
      'web-torrent.peer-limit',
    );

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

  getTorrents(): WebTorrentTorrent[] {
    const webtorrent = this.getClient();

    return webtorrent.torrents;
  }

  async getTorrent(infoHash: string): Promise<WebTorrentTorrent> {
    const webtorrent = this.getClient();

    const torrent = await webtorrent.get(infoHash);

    if (!torrent) {
      throw new NotFoundException(`A(z) "${infoHash}" torrent nem található.`);
    }

    return torrent;
  }

  addTorrent(payload: TorrentClientToAddTorrent): Promise<WebTorrentTorrent> {
    const webtorrent = this.getClient();

    return new Promise((resolve, reject) => {
      const { parsedTorrent, downloadFullTorrent = false } = payload;

      const torrent = webtorrent.add(
        parsedTorrent,
        {
          path: this.downloadsDir,
          storeCacheSlots: this.storeCacheSlots,
          deselect: !downloadFullTorrent,
        },
        (torrent) => {
          this.logger.log(
            `🎬 "${torrent.name}" nevű torrent hozzáadva a WebTorrent-hez.`,
          );

          resolve(torrent);
        },
      );

      torrent.once('error', reject);
    });
  }

  async deleteTorrent(infoHash: string): Promise<WebTorrentTorrent> {
    const webtorrent = this.getClient();

    const torrent = await this.getTorrent(infoHash);

    await webtorrent.remove(torrent, { destroyStore: true });

    this.logger.log(
      `🗑️ "${torrent.name}" nevű torrent törölve a WebTorrent-ből.`,
    );

    return torrent;
  }

  private getClient() {
    if (!this.client) {
      throw new InternalServerErrorException();
    }

    return this.client;
  }
}
