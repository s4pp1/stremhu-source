import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { EntityManager, Repository, SelectQueryBuilder } from 'typeorm';

import { TrackerCredential } from '../credentials/entity/tracker-credential.entity';
import { TrackerEnum } from '../enum/tracker.enum';
import { TrackerCoreToCreate } from '../type/tracker-core-to-create';

@Injectable()
export class TrackersStore {
  constructor(
    @InjectRepository(TrackerCredential)
    private readonly trackerRepository: Repository<TrackerCredential>,
  ) {}

  protected getRepository(
    manager?: EntityManager,
  ): Repository<TrackerCredential> {
    return manager
      ? manager.getRepository(TrackerCredential)
      : this.trackerRepository;
  }

  async create(
    payload: TrackerCoreToCreate,
    manager?: EntityManager,
  ): Promise<TrackerCredential> {
    const repository = this.getRepository(manager);

    const entity = repository.create(payload);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<TrackerCredential>,
    ) => SelectQueryBuilder<TrackerCredential>,
  ): Promise<TrackerCredential[]> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('tracker');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const items = await queryBuilder.getMany();
    return items;
  }

  async findOne(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<TrackerCredential>,
    ) => SelectQueryBuilder<TrackerCredential>,
  ): Promise<TrackerCredential | null> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('tracker');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const item = await queryBuilder.getOne();
    return item;
  }

  async findOneByTracker(tracker: TrackerEnum) {
    return this.findOne((qb) => {
      qb.where('tracker.tracker = :tracker', { tracker });
      return qb;
    });
  }

  async remove(
    entity: TrackerCredential,
    manager?: EntityManager,
  ): Promise<TrackerCredential> {
    const repository = this.getRepository(manager);
    await repository.remove(entity);
    return entity;
  }
}
