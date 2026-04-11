import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import {
  DeepPartial,
  EntityManager,
  Repository,
  SelectQueryBuilder,
} from 'typeorm';

import { Pairing } from '../entity/pairing.entity';

@Injectable()
export class PairingsStore {
  constructor(
    @InjectRepository(Pairing)
    private readonly pairingRepository: Repository<Pairing>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<Pairing> {
    return manager ? manager.getRepository(Pairing) : this.pairingRepository;
  }

  createEntity(entity: DeepPartial<Pairing>): Pairing {
    const repository = this.getRepository();
    return repository.create(entity);
  }

  async createOrUpdate(
    entity: Pairing,
    manager?: EntityManager,
  ): Promise<Pairing> {
    const repository = this.getRepository(manager);
    return repository.save(entity);
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<Pairing>,
    ) => SelectQueryBuilder<Pairing>,
  ): Promise<Pairing[]> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('pairing');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const items = await queryBuilder.getMany();
    return items;
  }

  async findOne(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<Pairing>,
    ) => SelectQueryBuilder<Pairing>,
  ): Promise<Pairing | null> {
    const repository = this.getRepository();

    let queryBuilder = repository.createQueryBuilder('pairing');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const item = await queryBuilder.getOne();
    return item;
  }

  async delete(entity: Pairing, manager?: EntityManager): Promise<void> {
    const repository = this.getRepository(manager);
    await repository.remove(entity);
  }
}
