import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import {
  DeepPartial,
  EntityManager,
  Repository,
  SelectQueryBuilder,
} from 'typeorm';

import { PersistedTorrent } from '../entity/torrent.entity';

@Injectable()
export class PersistedTorrentsStore {
  constructor(
    @InjectRepository(PersistedTorrent)
    private readonly torrentRepository: Repository<PersistedTorrent>,
  ) {}

  protected getRepository(
    manager?: EntityManager,
  ): Repository<PersistedTorrent> {
    return manager
      ? manager.getRepository(PersistedTorrent)
      : this.torrentRepository;
  }

  createEntity(entity: DeepPartial<PersistedTorrent>): PersistedTorrent {
    const repository = this.getRepository();
    return repository.create(entity);
  }

  async createOrUpdate(
    entity: PersistedTorrent,
    manager?: EntityManager,
  ): Promise<PersistedTorrent> {
    const repository = this.getRepository(manager);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<PersistedTorrent>,
    ) => SelectQueryBuilder<PersistedTorrent>,
  ): Promise<PersistedTorrent[]> {
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
      queryBuilder: SelectQueryBuilder<PersistedTorrent>,
    ) => SelectQueryBuilder<PersistedTorrent>,
  ): Promise<PersistedTorrent | null> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('torrent');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const item = await queryBuilder.getOne();
    return item;
  }

  async delete(
    entity: PersistedTorrent,
    manager?: EntityManager,
  ): Promise<void> {
    const repository = this.getRepository(manager);
    await repository.remove(entity);
  }
}
