import { ApiProperty } from '@nestjs/swagger';
import {
  IsBoolean,
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
} from 'class-validator';

import { UserRoleEnum } from '../enum/user-role.enum';

export class UpdateUserDto {
  /** Felhasználónév */
  @IsOptional()
  @IsString()
  username?: string;

  /** Jelszó */
  @IsOptional()
  @IsString()
  password?: string;

  /** Felhasználói szerepkör */
  @IsOptional()
  @IsEnum(UserRoleEnum)
  @ApiProperty({
    enum: UserRoleEnum,
    enumName: 'UserRoleEnum',
    required: false,
  })
  userRole?: UserRoleEnum;

  /** Torrent seed limit */
  @IsOptional()
  @IsNumber()
  torrentSeed?: number | null;

  /** Csak a legjobb torrentek megjelenítése */
  @IsOptional()
  @IsBoolean()
  onlyBestTorrent?: boolean;
}
