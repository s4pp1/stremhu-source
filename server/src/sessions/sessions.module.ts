import { Module } from '@nestjs/common';
import { TypeOrmModule, getRepositoryToken } from '@nestjs/typeorm';
import { Repository } from 'typeorm';

import { Session } from './entity/session.entity';
import { SessionsService } from './sessions.service';

@Module({
  imports: [TypeOrmModule.forFeature([Session])],
  providers: [
    {
      provide: SessionsService,
      useFactory: (repo: Repository<Session>) => new SessionsService(repo),
      inject: [getRepositoryToken(Session)],
    },
  ],
  exports: [SessionsService],
})
export class SessionsModule {}
