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
  @IsString()
  @ApiProperty()
  label: string;

  @IsString()
  @ApiProperty()
  description: string;
}

export class TrackerPreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.TRACKER)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.TRACKER,
  })
  value: PreferenceEnum.TRACKER;

  @IsArray()
  @ApiProperty({
    type: TrackerMetaDto,
    isArray: true,
  })
  items: TrackerMetaDto[];
}

export class LanguagePreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.LANGUAGE,
  })
  value: PreferenceEnum.LANGUAGE;

  @IsArray()
  @ApiProperty({
    type: LanguageMetaDto,
    isArray: true,
  })
  items: LanguageMetaDto[];
}

export class ResolutionPreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.RESOLUTION,
  })
  value: PreferenceEnum.RESOLUTION;

  @IsArray()
  @ApiProperty({
    type: ResolutionMetaDto,
    isArray: true,
  })
  items: ResolutionMetaDto[];
}

export class VideoQualityPreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.VIDEO_QUALITY,
  })
  value: PreferenceEnum.VIDEO_QUALITY;

  @IsArray()
  @ApiProperty({
    type: VideoQualityMetaDto,
    isArray: true,
  })
  items: VideoQualityMetaDto[];
}

export class SourcePreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.SOURCE,
  })
  value: PreferenceEnum.SOURCE;

  @IsArray()
  @ApiProperty({
    type: SourceMetaDto,
    isArray: true,
  })
  items: SourceMetaDto[];
}

export class AudioQualityPreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.AUDIO_QUALITY,
  })
  value: PreferenceEnum.AUDIO_QUALITY;

  @IsArray()
  @ApiProperty({
    type: AudioQualityMetaDto,
    isArray: true,
  })
  items: AudioQualityMetaDto[];
}

export class AudioSpatialPreferenceMetaDto extends BasePreferenceMetaDto {
  @Equals(PreferenceEnum.AUDIO_SPATIAL)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.AUDIO_SPATIAL,
  })
  value: PreferenceEnum.AUDIO_SPATIAL;

  @IsArray()
  @ApiProperty({
    type: AudioSpatialMetaDto,
    isArray: true,
  })
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
