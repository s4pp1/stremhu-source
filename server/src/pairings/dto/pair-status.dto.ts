import { IsOptional, IsString } from 'class-validator';

import { PairingStatusEnum } from '../enum/pairing-status.enum';

export class PairStatusDto {
  /** A párosítás állapota (pending, linked, expired) */
  status: PairingStatusEnum;

  /** A felhasználó API tokenje (csak 'linked' állapot esetén) */
  @IsOptional()
  @IsString()
  token?: string;
}
