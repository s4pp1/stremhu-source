import { ApiProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import {
  IsBoolean,
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
  IsUUID,
} from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';

import { UserRoleEnum } from '../enum/user-role.enum';

export class UserDto {
  /** Felhasználó egyedi azonosítója */
  @IsUUID()
  id: string;

  /** Felhasználónév */
  @IsString()
  username: string;

  @Exclude()
  @IsOptional()
  @IsString()
  passwordHash: string | null;

  /** API token */
  @IsString()
  token: string;

  /** Felhasználói szerepkör */
  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  userRole: UserRoleEnum;

  /** Torrent seed limit */
  @IsNullable()
  @IsNumber()
  torrentSeed: number | null;

  /** Csak a legjobb torrentek megjelenítése */
  @IsBoolean()
  onlyBestTorrent: boolean;
}
