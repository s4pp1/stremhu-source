import { Expose } from 'class-transformer';
import { IsOptional, IsString } from 'class-validator';

import { PairingStatusEnum } from '../enum/pairing-status.enum';

export class PairStatusDto {
  /** A párosítás állapota (pending, linked, expired) */
  @Expose()
  status: PairingStatusEnum;

  /** A felhasználó API tokenje (csak 'linked' állapot esetén) */
  @Expose()
  @IsOptional()
  @IsString()
  token?: string;
}
