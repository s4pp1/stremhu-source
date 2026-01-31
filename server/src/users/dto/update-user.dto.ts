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
import { AudioCodecEnum } from 'src/stremio/streams/enum/audio-codec.enum';
import { SourceTypeEnum } from 'src/stremio/streams/enum/source-type.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

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
