import { Resolution } from '@ctrl/video-filename-parser';
import { ApiProperty } from '@nestjs/swagger';
import {
  ArrayNotEmpty,
  ArrayUnique,
  IsArray,
  IsBoolean,
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
} from 'class-validator';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

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
  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
    isArray: true,
    required: false,
  })
  torrentVideoQualities?: VideoQualityEnum[];

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

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  onlyBestTorrent?: boolean;
}
