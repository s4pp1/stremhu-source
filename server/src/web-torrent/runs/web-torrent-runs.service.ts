import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { FindManyOptions, Repository } from 'typeorm';

import { WebTorrentRun } from './entity/web-torrent-run.entity';
import { WebTorrentRunToCreate } from './web-torrent-runs.types';

@Injectable()
export class WebTorrentRunsService {
  private readonly logger = new Logger(WebTorrentRunsService.name);

  constructor(
    @InjectRepository(WebTorrentRun)
    private readonly webTorrentRunRepository: Repository<WebTorrentRun>,
  ) {}

  async create(payload: WebTorrentRunToCreate): Promise<WebTorrentRun> {
    const webTorrentRunEntity = this.webTorrentRunRepository.create(payload);
    return this.webTorrentRunRepository.save(webTorrentRunEntity);
  }

  async find(options?: FindManyOptions<WebTorrentRun>) {
    const webTorrentRuns = await this.webTorrentRunRepository.find(options);
    return webTorrentRuns;
  }

  async findOne(infoHash: string) {
    const webTorrentRun = await this.webTorrentRunRepository.findOne({
      where: {
        infoHash,
      },
    });

    return webTorrentRun;
  }

  async delete(infoHash: string) {
    const webTorrentRun = await this.findOne(infoHash);

    if (!webTorrentRun) {
      this.logger.error(`Nem található futó torrent: "${infoHash}"`);
      return;
    }

    await this.webTorrentRunRepository.remove(webTorrentRun);
  }

  async flushUpload(infoHash: string, sessionBytes: number) {
    if (sessionBytes <= 0) return;

    await this.webTorrentRunRepository
      .createQueryBuilder()
      .update()
      .set({
        uploaded: () => `uploaded + ${sessionBytes}`,
      })
      .where('info_hash = :infoHash', { infoHash })
      .execute();
  }
}
