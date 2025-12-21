import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { User } from '../entity/user.entity';
import { UsersStore } from './users.store';

@Module({
  imports: [TypeOrmModule.forFeature([User])],
  providers: [UsersStore],
  exports: [UsersStore],
})
export class UsersCoreModule {}
