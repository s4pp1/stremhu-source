import { ApiProperty } from '@nestjs/swagger';
import { ClassConstructor } from 'class-transformer';
import { Equals, IsArray, IsString } from 'class-validator';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { AudioQualityMetaDto } from './audio-quality-meta.dto';
import { LanguageMetaDto } from './language-meta.dto';
import { ResolutionMetaDto } from './resolution-meta.dto';
import { SourceMetaDto } from './source-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { VideoQualityMetaDto } from './video-quality-meta.dto';

export class TrackerPreferenceMetaDto {
  @Equals(PreferenceEnum.TRACKER)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.TRACKER,
  })
  value: PreferenceEnum.TRACKER;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: TrackerMetaDto,
    isArray: true,
  })
  items: TrackerMetaDto[];
}

export class LanguagePreferenceMetaDto {
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.LANGUAGE,
  })
  value: PreferenceEnum.LANGUAGE;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: LanguageMetaDto,
    isArray: true,
  })
  items: LanguageMetaDto[];
}

export class ResolutionPreferenceMetaDto {
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.RESOLUTION,
  })
  value: PreferenceEnum.RESOLUTION;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: ResolutionMetaDto,
    isArray: true,
  })
  items: ResolutionMetaDto[];
}

export class VideoQualityPreferenceMetaDto {
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.VIDEO_QUALITY,
  })
  value: PreferenceEnum.VIDEO_QUALITY;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: VideoQualityMetaDto,
    isArray: true,
  })
  items: VideoQualityMetaDto[];
}

export class SourcePreferenceMetaDto {
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.SOURCE,
  })
  value: PreferenceEnum.SOURCE;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: SourceMetaDto,
    isArray: true,
  })
  items: SourceMetaDto[];
}

export class AudioQualityPreferenceMetaDto {
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.AUDIO_QUALITY,
  })
  value: PreferenceEnum.AUDIO_QUALITY;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: AudioQualityMetaDto,
    isArray: true,
  })
  items: AudioQualityMetaDto[];
}

export type PreferenceMetaDto =
  | TrackerPreferenceMetaDto
  | LanguagePreferenceMetaDto
  | ResolutionPreferenceMetaDto
  | VideoQualityPreferenceMetaDto
  | SourcePreferenceMetaDto
  | AudioQualityPreferenceMetaDto;

type PreferenceMetaDtoConstructor = ClassConstructor<PreferenceMetaDto>;

export const PREFERENCE_META_SWAGGER_MODELS: readonly PreferenceMetaDtoConstructor[] =
  [
    TrackerPreferenceMetaDto,
    LanguagePreferenceMetaDto,
    ResolutionPreferenceMetaDto,
    VideoQualityPreferenceMetaDto,
    SourcePreferenceMetaDto,
    AudioQualityPreferenceMetaDto,
  ];
