import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { isUndefined, omitBy } from 'lodash';
import { EntityManager, Repository, SelectQueryBuilder } from 'typeorm';

import { User } from '../entity/user.entity';
import { UserCoreToCreate } from '../type/user-core-to-create.type';
import { UserCoreToUpdate } from '../type/user-core-to-update.type';

@Injectable()
export class UsersStore {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<User> {
    return manager ? manager.getRepository(User) : this.userRepository;
  }

  async create(payload: UserCoreToCreate, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const entity = repository.create(payload);

    const user = repository.save(entity);

    return user;
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<User>,
    ) => SelectQueryBuilder<User>,
  ) {
    let queryBuilder = this.userRepository.createQueryBuilder('user');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const users = await queryBuilder.getMany();
    return users;
  }

  async findOne(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<User>,
    ) => SelectQueryBuilder<User>,
  ): Promise<User | null> {
    let queryBuilder = this.userRepository.createQueryBuilder('user');

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const user = await queryBuilder.getOne();
    return user;
  }

  async findOneById(id: string): Promise<User | null> {
    const item = await this.findOne((qb) => {
      qb.where('user.id = :id', { id });

      return qb;
    });

    return item;
  }

  async findOneByIdOrThrow(id: string) {
    const user = await this.findOneById(id);

    if (!user) {
      throw new NotFoundException(`Nincs ilyen felhasználó!`);
    }

    return user;
  }

  async updateOneOrThrow(
    userId: string,
    payload: UserCoreToUpdate,
    manager?: EntityManager,
  ) {
    const repository = this.getRepository(manager);

    const user = await this.findOneByIdOrThrow(userId);

    const updateData = omitBy(payload, isUndefined);

    await repository.update({ id: userId }, updateData);

    return { ...user, ...updateData };
  }

  async deleteOrThrow(userId: string, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const user = await this.findOneByIdOrThrow(userId);

    await repository.delete({ id: user.id });
  }
}
