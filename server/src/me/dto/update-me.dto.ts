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

import { AudioCodecEnum } from 'src/preference-items/enum/audio-codec.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { SourceTypeEnum } from 'src/preference-items/enum/source-type.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

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
  @IsEnum(AudioCodecEnum, { each: true })
  @ApiProperty({
    enum: AudioCodecEnum,
    enumName: 'AudioCodecEnum',
    isArray: true,
    required: false,
  })
  torrentAudioCodecs?: AudioCodecEnum[];

  @IsOptional()
  @IsArray()
  @ArrayNotEmpty()
  @ArrayUnique()
  @IsEnum(SourceTypeEnum, { each: true })
  @ApiProperty({
    enum: SourceTypeEnum,
    enumName: 'SourceTypeEnum',
    isArray: true,
    required: false,
  })
  torrentSourceTypes?: SourceTypeEnum[];

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
