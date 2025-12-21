import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { EntityManager, Repository, SelectQueryBuilder } from 'typeorm';

import { Tracker } from '../entity/tracker.entity';
import { TrackerEnum } from '../enum/tracker.enum';
import { TrackerCoreToCreate } from '../type/tracker-core-to-create';

@Injectable()
export class TrackersStore {
  constructor(
    @InjectRepository(Tracker)
    private readonly trackerRepository: Repository<Tracker>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<Tracker> {
    return manager ? manager.getRepository(Tracker) : this.trackerRepository;
  }

  async create(
    payload: TrackerCoreToCreate,
    manager?: EntityManager,
  ): Promise<Tracker> {
    const repository = this.getRepository(manager);

    const entity = repository.create(payload);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<Tracker>,
    ) => SelectQueryBuilder<Tracker>,
  ): Promise<Tracker[]> {
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
      queryBuilder: SelectQueryBuilder<Tracker>,
    ) => SelectQueryBuilder<Tracker>,
  ): Promise<Tracker | null> {
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

  async updateOne(payload: Tracker, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const item = await repository.save(payload);

    return item;
  }

  async remove(entity: Tracker, manager?: EntityManager): Promise<Tracker> {
    const repository = this.getRepository(manager);
    await repository.remove(entity);
    return entity;
  }
}
