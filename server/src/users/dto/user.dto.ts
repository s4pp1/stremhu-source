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
  @IsUUID()
  @ApiProperty({ format: 'uuid' })
  id: string;

  @IsString()
  @ApiProperty()
  username: string;

  @Exclude()
  @IsOptional()
  @IsString()
  passwordHash: string | null;

  @IsString()
  @ApiProperty()
  token: string;

  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  userRole: UserRoleEnum;

  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true })
  torrentSeed: number | null;

  @IsBoolean()
  @ApiProperty({ type: 'boolean' })
  onlyBestTorrent: boolean;
}
