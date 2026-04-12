import { Injectable, Logger } from '@nestjs/common';
import { setTimeout as sleep } from 'node:timers/promises';

import {
  RelayTorrent,
  UpdateRelayTorrent,
  UpdateSettings,
  addTorrent,
  deleteTorrent,
  getTorrent,
  getTorrentState,
  getTorrents,
  update,
  updateTorrent,
} from './client/relay-client';
import { RelayRuntimeService } from './relay-runtime.service';
import { AddRelayTorrent } from './type/add-relay-torrent.type';

@Injectable()
export class RelayService {
  private readonly logger = new Logger(RelayService.name);

  constructor(private readonly relayRuntimeService: RelayRuntimeService) {}

  async updateConfig(payload: UpdateSettings) {
    await this.relayRuntimeService.request(() => update(payload));
  }

  async getTorrents(): Promise<RelayTorrent[]> {
    return this.relayRuntimeService.request(() => getTorrents());
  }

  async getTorrent(infoHash: string): Promise<RelayTorrent | null> {
    try {
      return await this.relayRuntimeService.request(() => getTorrent(infoHash));
    } catch {
      return null;
    }
  }

  async addTorrent(payload: AddRelayTorrent): Promise<RelayTorrent> {
    const torrent = await this.relayRuntimeService.request(() =>
      addTorrent({
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
      const { state, progress } = await getTorrentState(torrent.infoHash);

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
      updateTorrent(infoHash, payload),
    );
  }

  async deleteTorrent(infoHash: string): Promise<RelayTorrent> {
    const torrent = await this.relayRuntimeService.request(() =>
      deleteTorrent(infoHash),
    );

    this.logger.log(`🗑️ "${infoHash}" torrent törölve a Relay-ből.`);

    return torrent;
  }
}
