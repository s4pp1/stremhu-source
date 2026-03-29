import { Inject, Injectable, Logger } from '@nestjs/common';
import { setTimeout as sleep } from 'node:timers/promises';

import {
  RelayClient,
  RelayTorrent,
  UpdateRelayTorrent,
  UpdateSettings,
} from './client';
import { RelayRuntimeService } from './relay-runtime.service';
import { RELAY_CLIENT } from './relay.token';
import { AddRelayTorrent } from './type/add-relay-torrent.type';

@Injectable()
export class RelayService {
  private readonly logger = new Logger(RelayService.name);

  constructor(
    @Inject(RELAY_CLIENT)
    private readonly relayClient: RelayClient,
    private readonly relayRuntimeService: RelayRuntimeService,
  ) {}

  async updateConfig(payload: UpdateSettings) {
    await this.relayRuntimeService.request(() =>
      this.relayClient.setting.update(payload),
    );
  }

  async getTorrents(): Promise<RelayTorrent[]> {
    return this.relayRuntimeService.request(() =>
      this.relayClient.torrents.getTorrents(),
    );
  }

  async getTorrent(infoHash: string): Promise<RelayTorrent | null> {
    try {
      return await this.relayRuntimeService.request(() =>
        this.relayClient.torrents.getTorrent(infoHash),
      );
    } catch {
      return null;
    }
  }

  async addTorrent(payload: AddRelayTorrent): Promise<RelayTorrent> {
    const torrent = await this.relayRuntimeService.request(() =>
      this.relayClient.torrents.addTorrent({
        torrentFilePath: payload.torrentFilePath,
        downloadFullTorrent: payload.downloadFullTorrent,
      }),
    );

    this.logger.log(`🎬 "${torrent.name}" torrent hozzáadva a Relay-hez.`);

    return torrent;
  }

  async addTorrentWithChecking(
    payload: AddRelayTorrent,
  ): Promise<RelayTorrent> {
    const torrent = await this.addTorrent(payload);

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
      await sleep(2000);
    }

    return torrent;
  }

  async updateTorrent(
    infoHash: string,
    payload: UpdateRelayTorrent,
  ): Promise<RelayTorrent> {
    return this.relayRuntimeService.request(() =>
      this.relayClient.torrents.updateTorrent(infoHash, payload),
    );
  }

  async deleteTorrent(infoHash: string): Promise<RelayTorrent> {
    const torrent = await this.relayRuntimeService.request(() =>
      this.relayClient.torrents.deleteTorrent(infoHash),
    );

    this.logger.log(`🗑️ "${infoHash}" torrent törölve a Relay-ből.`);

    return torrent;
  }
}
