import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import {
  DeepPartial,
  EntityManager,
  Repository,
  SelectQueryBuilder,
} from 'typeorm';

import { UserPreference } from '../entity/user-preference.entity';

@Injectable()
export class UserPreferencesStore {
  constructor(
    @InjectRepository(UserPreference)
    private readonly torrentRepository: Repository<UserPreference>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<UserPreference> {
    return manager
      ? manager.getRepository(UserPreference)
      : this.torrentRepository;
  }

  createEntity(entity: DeepPartial<UserPreference>): UserPreference {
    const repository = this.getRepository();
    return repository.create(entity);
  }

  async createOrUpdate(
    entity: UserPreference,
    manager?: EntityManager,
  ): Promise<UserPreference> {
    const repository = this.getRepository(manager);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<UserPreference>,
    ) => SelectQueryBuilder<UserPreference>,
  ): Promise<UserPreference[]> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('user-preference');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const items = await queryBuilder.getMany();
    return items;
  }

  async findOne(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<UserPreference>,
    ) => SelectQueryBuilder<UserPreference>,
  ): Promise<UserPreference | null> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('user-preference');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const item = await queryBuilder.getOne();
    return item;
  }

  async delete(entity: UserPreference, manager?: EntityManager): Promise<void> {
    const repository = this.getRepository(manager);
    await repository.remove(entity);
  }
}
