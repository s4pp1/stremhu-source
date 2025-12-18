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

export class UpdateMeDto {
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
  @IsArray()
  @ArrayNotEmpty()
  @ArrayUnique()
  @IsEnum(Resolution, { each: true })
  @ApiProperty({ enum: Resolution, enumName: 'ResolutionEnum', isArray: true })
  torrentResolutions?: Resolution[];

  @IsOptional()
  @IsArray()
  @ArrayNotEmpty()
  @ArrayUnique()
  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum', isArray: true })
  torrentLanguages?: LanguageEnum[];

  @IsOptional()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true })
  torrentSeed?: number | null;
}
