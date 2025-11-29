import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Algorithm, hash } from '@node-rs/argon2';
import { isUndefined, omitBy } from 'lodash';
import { randomUUID } from 'node:crypto';
import { EntityManager, Repository, SelectQueryBuilder } from 'typeorm';

import { User } from './entity/user.entity';
import { UserToCreate } from './type/user-to-create.type';
import { UserToUpdate } from './type/user-to-update.type';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<User> {
    return manager ? manager.getRepository(User) : this.userRepository;
  }

  async create(payload: UserToCreate, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const users = await this.find((queryBuilder) =>
      queryBuilder.where('username = :username', {
        username: payload.username,
      }),
    );

    if (users.length !== 0) {
      throw new NotFoundException();
    }

    let passwordHash: string | null = null;
    if (payload.password) {
      passwordHash = await this.hashPassword(payload.password);
    }

    const userEntity = repository.create({
      ...payload,
      passwordHash,
      stremioToken: randomUUID(),
    });
    const user = repository.save(userEntity);

    return user;
  }

  async find(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<User>,
    ) => SelectQueryBuilder<User>,
  ) {
    let queryBuilder = this.userRepository.createQueryBuilder();

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
  ) {
    let queryBuilder = this.userRepository.createQueryBuilder();

    if (configureQuery) {
      queryBuilder = configureQuery(queryBuilder);
    }

    const user = await queryBuilder.getOne();
    return user;
  }

  async findOneOrThrow(
    configureQuery?: (
      queryBuilder: SelectQueryBuilder<User>,
    ) => SelectQueryBuilder<User>,
  ) {
    const user = await this.findOne(configureQuery);

    if (!user) {
      throw new NotFoundException();
    }

    return user;
  }

  async updateUsernameOrThrow(
    userId: string,
    username: string,
    manager?: EntityManager,
  ) {
    const existUser = await this.findOne((qb) =>
      qb.where('username = :username', { username }),
    );

    if (existUser) {
      throw new BadRequestException('A fejlasználónév már használatban van.');
    }

    const user = await this.findOneOrThrow((qb) =>
      qb.where('id = :userId', { userId }),
    );

    const repository = this.getRepository(manager);

    await repository.update({ id: userId }, { username });

    return { ...user, username };
  }

  async updateOneOrThrow(
    userId: string,
    payload: UserToUpdate,
    manager?: EntityManager,
  ) {
    const repository = this.getRepository(manager);

    const user = await this.findOneOrThrow((qb) =>
      qb.where('id = :userId', { userId }),
    );

    const updateData = omitBy(payload, isUndefined);

    if (payload.password) {
      const passwordHash = await this.hashPassword(payload.password);
      delete updateData.password;
      updateData.passwordHash = passwordHash;
    }

    await repository.update({ id: userId }, updateData);

    return { ...user, ...updateData };
  }

  async regenerateStremioToken(userId: string, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const user = await this.findOneOrThrow((queryBuilder) =>
      queryBuilder.where('id = :userId', { userId }),
    );

    const stremioToken = randomUUID();
    await repository.update({ id: userId }, { stremioToken });

    return { ...user, stremioToken };
  }

  async deleteOrThrow(userId: string, manager?: EntityManager) {
    const repository = this.getRepository(manager);

    const user = await this.findOneOrThrow((queryBuilder) =>
      queryBuilder.where('id = :userId', { userId }),
    );

    await repository.delete({ id: user.id });
  }

  private async hashPassword(password: string) {
    const passwordHash = await hash(password);

    return passwordHash;
  }
}
