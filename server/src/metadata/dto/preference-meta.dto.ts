import { ApiProperty } from '@nestjs/swagger';
import { ClassConstructor } from 'class-transformer';
import { Equals, IsArray, IsString } from 'class-validator';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { AudioQualityMetaDto } from './audio-quality-meta.dto';
import { AudioSpatialMetaDto } from './audio-spatial-meta.dto';
import { LanguageMetaDto } from './language-meta.dto';
import { ResolutionMetaDto } from './resolution-meta.dto';
import { SourceMetaDto } from './source-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { VideoQualityMetaDto } from './video-quality-meta.dto';

export class BasePreferenceMetaDto {
  /** Megjelenített név */
  @IsString()
  label: string;

  /** Leírás */
  @IsString()
  description: string;
}

export class TrackerPreferenceMetaDto extends BasePreferenceMetaDto {
  /** Tracker preferencia azonosító */
  @Equals(PreferenceEnum.TRACKER)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.TRACKER;

  /** Tracker elemek listája */
  @IsArray()
  items: TrackerMetaDto[];
}

export class LanguagePreferenceMetaDto extends BasePreferenceMetaDto {
  /** Nyelv preferencia azonosító */
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.LANGUAGE;

  /** Nyelv elemek listája */
  @IsArray()
  items: LanguageMetaDto[];
}

export class ResolutionPreferenceMetaDto extends BasePreferenceMetaDto {
  /** Felbontás preferencia azonosító */
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.RESOLUTION;

  /** Felbontás elemek listája */
  @IsArray()
  items: ResolutionMetaDto[];
}

export class VideoQualityPreferenceMetaDto extends BasePreferenceMetaDto {
  /** Videó minőség preferencia azonosító */
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.VIDEO_QUALITY;

  /** Videó minőség elemek listája */
  @IsArray()
  items: VideoQualityMetaDto[];
}

export class SourcePreferenceMetaDto extends BasePreferenceMetaDto {
  /** Forrás preferencia azonosító */
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.SOURCE;

  /** Forrás elemek listája */
  @IsArray()
  items: SourceMetaDto[];
}

export class AudioQualityPreferenceMetaDto extends BasePreferenceMetaDto {
  /** Audió minőség preferencia azonosító */
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.AUDIO_QUALITY;

  /** Audió minőség elemek listája */
  @IsArray()
  items: AudioQualityMetaDto[];
}

export class AudioSpatialPreferenceMetaDto extends BasePreferenceMetaDto {
  /** Térhatású hang preferencia azonosító */
  @Equals(PreferenceEnum.AUDIO_SPATIAL)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  value: PreferenceEnum.AUDIO_SPATIAL;

  /** Térhatású hang elemek listája */
  @IsArray()
  items: AudioSpatialMetaDto[];
}

export type PreferenceMetaDto =
  | TrackerPreferenceMetaDto
  | LanguagePreferenceMetaDto
  | ResolutionPreferenceMetaDto
  | VideoQualityPreferenceMetaDto
  | SourcePreferenceMetaDto
  | AudioQualityPreferenceMetaDto
  | AudioSpatialPreferenceMetaDto;

type PreferenceMetaDtoConstructor = ClassConstructor<PreferenceMetaDto>;

export const PREFERENCE_META_SWAGGER_MODELS: readonly PreferenceMetaDtoConstructor[] =
  [
    TrackerPreferenceMetaDto,
    LanguagePreferenceMetaDto,
    ResolutionPreferenceMetaDto,
    VideoQualityPreferenceMetaDto,
    SourcePreferenceMetaDto,
    AudioQualityPreferenceMetaDto,
    AudioSpatialPreferenceMetaDto,
  ];
