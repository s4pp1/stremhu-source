import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import {
  IsBoolean,
  IsDate,
  IsEnum,
  IsNumber,
  IsString,
  IsUUID,
} from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

import { UserRoleEnum } from '../enum/user-role.enum';

export class UserDto {
  /** Felhasználó egyedi azonosítója */
  @Expose()
  @IsUUID()
  id: string;

  /** Felhasználónév */
  @Expose()
  @IsString()
  username: string;

  /** API token */
  @Expose()
  @IsString()
  token: string;

  /** Felhasználói szerepkör */
  @Expose()
  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  userRole: UserRoleEnum;

  /** Torrent seed limit */
  @Expose()
  @IsNullable()
  @IsNumber()
  torrentSeed: number | null;

  /** Csak a legjobb torrentek megjelenítése */
  @Expose()
  @IsBoolean()
  onlyBestTorrent: boolean;

  /** Utolsó frissítés időpontja */
  @Expose()
  @IsDate()
  updatedAt: Date;

  /** Létrehozás időpontja */
  @Expose()
  @IsDate()
  createdAt: Date;
}
