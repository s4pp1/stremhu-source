import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import session from 'express-session';
import { Repository } from 'typeorm';

import { THIRTY_DAYS_MS } from 'src/app.constant';

import { Session } from './entity/session.entity';

@Injectable()
export class SessionsService extends session.Store {
  private readonly logger = new Logger(SessionsService.name);

  constructor(private readonly sessionRepository: Repository<Session>) {
    super();
  }

  get(sid: string, cb: (err?: any, sess?: session.SessionData | null) => void) {
    this.sessionRepository
      .findOne({ where: { sid } })
      .then((row) => {
        if (!row || row.expires < Date.now()) {
          return cb(undefined, null);
        }
        const parsedSession = JSON.parse(row.data) as session.SessionData;
        cb(undefined, parsedSession);
      })
      .catch(cb);
  }

  set(sid: string, sess: session.SessionData, cb: (err?: any) => void) {
    const sessionEntity = this.sessionRepository.create({
      sid,
      data: JSON.stringify(sess),
      expires: Date.now() + THIRTY_DAYS_MS,
    });

    this.sessionRepository
      .save(sessionEntity)
      .then(() => cb())
      .catch(cb);
  }

  destroy(sid: string, cb: (err?: any) => void) {
    this.sessionRepository
      .delete({ sid })
      .then(() => cb())
      .catch(cb);
  }

  touch(sid: string, _: session.SessionData, cb: (err?: any) => void) {
    const expires = Date.now() + THIRTY_DAYS_MS;
    this.sessionRepository
      .update({ sid }, { expires })
      .then(() => cb())
      .catch(cb);
  }

  @Cron(CronExpression.EVERY_HOUR)
  async removeExpired() {
    const now = Date.now();
    await this.sessionRepository
      .createQueryBuilder()
      .delete()
      .where('expires < :now', { now })
      .execute();
  }
}
