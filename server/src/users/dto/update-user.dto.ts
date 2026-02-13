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
  @IsOptional()
  @IsString()
  @ApiProperty({
    type: 'string',
    required: false,
  })
  username?: string;

  @IsOptional()
  @IsString()
  @ApiProperty({
    type: 'string',
    required: false,
  })
  password?: string;

  @IsOptional()
  @IsEnum(UserRoleEnum)
  @ApiProperty({
    enum: UserRoleEnum,
    enumName: 'UserRoleEnum',
    required: false,
  })
  userRole?: UserRoleEnum;

  @IsOptional()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true, required: false })
  torrentSeed?: number | null;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  onlyBestTorrent?: boolean;
}
