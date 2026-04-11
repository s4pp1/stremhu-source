import {
  Injectable,
  Logger,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { customAlphabet } from 'nanoid';
import { v4 as uuidv4 } from 'uuid';

import { User } from '../users/entity/user.entity';
import { PairingsStore } from './core/pairings.store';
import { PairingStatus } from './enum/pairing-status.enum';

const PAIRING_EXPIRY_MS = 10 * 60 * 1000;

@Injectable()
export class PairingsService {
  private readonly logger = new Logger(PairingsService.name);
  private readonly nanoid = customAlphabet('0123456789', 4);

  constructor(private readonly pairingsStore: PairingsStore) {}

  async generatePairingCodes() {
    let userCode = '';
    let isUnique = false;

    while (!isUnique) {
      userCode = this.nanoid();

      const existingPairing = await this.pairingsStore.findOne((qb) =>
        qb.where('pairing.userCode = :userCode', { userCode }),
      );

      if (!existingPairing) isUnique = true;
    }

    const deviceCode = uuidv4();
    const expiresAt = new Date(Date.now() + PAIRING_EXPIRY_MS);

    const pairing = this.pairingsStore.createEntity({
      userCode,
      deviceCode,
      expiresAt,
      status: PairingStatus.PENDING,
    });

    await this.pairingsStore.createOrUpdate(pairing);

    return {
      userCode,
      deviceCode,
      expiresAt,
    };
  }

  async pollPairingStatus(deviceCode: string) {
    const pairing = await this.pairingsStore.findOne((qb) => {
      qb.leftJoinAndSelect('pairing.user', 'user').where(
        'pairing.deviceCode = :deviceCode',
        { deviceCode },
      );
      return qb;
    });

    if (!pairing) {
      throw new NotFoundException('Érvénytelen eszköz kód!');
    }

    if (pairing.expiresAt < new Date()) {
      await this.pairingsStore.createOrUpdate({
        ...pairing,
        status: PairingStatus.EXPIRED,
      });

      throw new UnauthorizedException('A párosítási kód lejárt!');
    }

    if (pairing.status === PairingStatus.LINKED && pairing.user) {
      return {
        status: PairingStatus.LINKED,
        token: pairing.user.token,
      };
    }

    return {
      status: pairing.status,
    };
  }

  async authorizePairingCode(userCode: string, user: User) {
    const pairing = await this.pairingsStore.findOne((qb) =>
      qb.where('pairing.userCode = :userCode', { userCode }),
    );

    if (!pairing) {
      throw new NotFoundException('Érvénytelen vagy lejárt kód!');
    }

    if (pairing.expiresAt < new Date()) {
      await this.pairingsStore.createOrUpdate({
        ...pairing,
        status: PairingStatus.EXPIRED,
      });
      throw new UnauthorizedException('A kód már lejárt!');
    }

    await this.pairingsStore.createOrUpdate({
      ...pairing,
      status: PairingStatus.LINKED,
      userId: user.id,
    });

    return { success: true };
  }

  @Cron(CronExpression.EVERY_HOUR)
  async cleanupExpiredPairings() {
    const now = new Date();

    const expiredPairings = await this.pairingsStore.find((qb) =>
      qb.where('pairing.expiresAt < :now', { now }),
    );

    for (const pairing of expiredPairings) {
      await this.pairingsStore.delete(pairing);
    }
  }
}
