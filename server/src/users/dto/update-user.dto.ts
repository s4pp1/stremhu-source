import { Resolution } from '@ctrl/video-filename-parser';
import { ApiProperty } from '@nestjs/swagger';
import {
  ArrayNotEmpty,
  ArrayUnique,
  IsArray,
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
} from 'class-validator';

import { LanguageEnum } from 'src/common/enum/language.enum';

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
  @IsArray()
  @ArrayNotEmpty()
  @ArrayUnique()
  @IsEnum(Resolution, { each: true })
  @ApiProperty({
    enum: Resolution,
    enumName: 'ResolutionEnum',
    isArray: true,
    required: false,
  })
  torrentResolutions?: Resolution[];

  @IsOptional()
  @IsArray()
  @ArrayNotEmpty()
  @ArrayUnique()
  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({
    enum: LanguageEnum,
    enumName: 'LanguageEnum',
    isArray: true,
    required: false,
  })
  torrentLanguages?: LanguageEnum[];

  @IsOptional()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true, required: false })
  torrentSeed?: number | null;
}
