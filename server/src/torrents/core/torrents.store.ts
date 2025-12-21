import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { EntityManager, Repository, SelectQueryBuilder } from 'typeorm';

import { Torrent } from '../entity/torrent.entity';
import { TorrentToCreate } from '../type/torrent-to-create.type';
import { TorrentToFlushUploaded } from '../type/torrent-to-flush-uploaded';

@Injectable()
export class TorrentsStore {
  constructor(
    @InjectRepository(Torrent)
    private readonly torrentRepository: Repository<Torrent>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<Torrent> {
    return manager ? manager.getRepository(Torrent) : this.torrentRepository;
  }

  async create(
    payload: TorrentToCreate,
    manager?: EntityManager,
  ): Promise<Torrent> {
    const repository = this.getRepository(manager);

    const entity = repository.create(payload);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<Torrent>,
    ) => SelectQueryBuilder<Torrent>,
  ): Promise<Torrent[]> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('torrent');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const items = await queryBuilder.getMany();
    return items;
  }

  async findOne(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<Torrent>,
    ) => SelectQueryBuilder<Torrent>,
  ): Promise<Torrent | null> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('torrent');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const item = await queryBuilder.getOne();
    return item;
  }

  async findOneByInfoHash(infoHash: string) {
    return this.findOne((qb) => {
      qb.where('torrent.infoHash = :infoHash', { infoHash });
      return qb;
    });
  }

  async findOneByInfoHashOrThrow(infoHash: string) {
    const item = await this.findOneByInfoHash(infoHash);

    if (!item) {
      throw new NotFoundException(`Nem található a(z) "${infoHash}" torrent.`);
    }

    return item;
  }

  async removeByInfoHash(infoHash: string, manager?: EntityManager) {
    const item = await this.findOneByInfoHashOrThrow(infoHash);

    const repository = this.getRepository(manager);

    await repository.remove(item);
  }

  async updateOne(payload: Torrent, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const torrent = await repository.save(payload);

    return torrent;
  }

  async flushUploaded(
    payload: TorrentToFlushUploaded,
    manager?: EntityManager,
  ): Promise<Torrent> {
    const { infoHash, sessionBytes } = payload;

    const item = await this.findOneByInfoHashOrThrow(infoHash);
    if (sessionBytes <= 0) return item;

    const repository = this.getRepository(manager);

    item.uploaded = item.uploaded + sessionBytes;

    const updated = {
      ...item,
      uploaded: item.uploaded + sessionBytes,
    };

    await repository.update({ infoHash: item.infoHash }, updated);

    return updated;
  }
}
