import { ApiProperty } from '@nestjs/swagger';
import type { ClassConstructor } from 'class-transformer';
import { Equals, IsEnum } from 'class-validator';

import { AudioSpatialEnum } from 'src/preference-items/enum/audio-feature.enum';
import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { PreferenceEnum } from '../enum/preference.enum';

export class TrackerPreferenceDto {
  @Equals(PreferenceEnum.TRACKER)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.TRACKER,
  })
  preference: PreferenceEnum.TRACKER;

  @IsEnum(TrackerEnum, { each: true })
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum', isArray: true })
  preferred: TrackerEnum[];

  @IsEnum(TrackerEnum, { each: true })
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum', isArray: true })
  blocked: TrackerEnum[];
}

export class LanguagePreferenceDto {
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.LANGUAGE,
  })
  preference: PreferenceEnum.LANGUAGE;

  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum', isArray: true })
  preferred: LanguageEnum[];

  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum', isArray: true })
  blocked: LanguageEnum[];
}

export class ResolutionPreferenceDto {
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.RESOLUTION,
  })
  preference: PreferenceEnum.RESOLUTION;

  @IsEnum(ResolutionEnum, { each: true })
  @ApiProperty({
    enum: ResolutionEnum,
    enumName: 'ResolutionEnum',
    isArray: true,
  })
  preferred: ResolutionEnum[];

  @IsEnum(ResolutionEnum, { each: true })
  @ApiProperty({
    enum: ResolutionEnum,
    enumName: 'ResolutionEnum',
    isArray: true,
  })
  blocked: ResolutionEnum[];
}

export class VideoQualityPreferenceDto {
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.VIDEO_QUALITY,
  })
  preference: PreferenceEnum.VIDEO_QUALITY;

  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
    isArray: true,
  })
  preferred: VideoQualityEnum[];

  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
    isArray: true,
  })
  blocked: VideoQualityEnum[];
}

export class SourcePreferenceDto {
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.SOURCE,
  })
  preference: PreferenceEnum.SOURCE;

  @IsEnum(SourceEnum, { each: true })
  @ApiProperty({
    enum: SourceEnum,
    enumName: 'SourceEnum',
    isArray: true,
  })
  preferred: SourceEnum[];

  @IsEnum(SourceEnum, { each: true })
  @ApiProperty({
    enum: SourceEnum,
    enumName: 'SourceEnum',
    isArray: true,
  })
  blocked: SourceEnum[];
}

export class AudioQualityPreferenceDto {
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.AUDIO_QUALITY,
  })
  preference: PreferenceEnum.AUDIO_QUALITY;

  @IsEnum(AudioQualityEnum, { each: true })
  @ApiProperty({
    enum: AudioQualityEnum,
    enumName: 'AudioQualityEnum',
    isArray: true,
  })
  preferred: AudioQualityEnum[];

  @IsEnum(AudioQualityEnum, { each: true })
  @ApiProperty({
    enum: AudioQualityEnum,
    enumName: 'AudioQualityEnum',
    isArray: true,
  })
  blocked: AudioQualityEnum[];
}

export class AudioSpatialPreferenceDto {
  @Equals(PreferenceEnum.AUDIO_SPATIAL)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
    example: PreferenceEnum.AUDIO_SPATIAL,
  })
  preference: PreferenceEnum.AUDIO_SPATIAL;

  @IsEnum(AudioSpatialEnum, { each: true })
  @ApiProperty({
    enum: AudioSpatialEnum,
    enumName: 'AudioSpatialEnum',
    isArray: true,
  })
  preferred: AudioSpatialEnum[];

  @IsEnum(AudioSpatialEnum, { each: true })
  @ApiProperty({
    enum: AudioSpatialEnum,
    enumName: 'AudioSpatialEnum',
    isArray: true,
  })
  blocked: AudioSpatialEnum[];
}

export type PreferenceDto =
  | TrackerPreferenceDto
  | LanguagePreferenceDto
  | ResolutionPreferenceDto
  | VideoQualityPreferenceDto
  | SourcePreferenceDto
  | AudioQualityPreferenceDto
  | AudioSpatialPreferenceDto;

type PreferenceDtoConstructor = ClassConstructor<PreferenceDto>;

export const PREFERENCE_SWAGGER_MODELS: readonly PreferenceDtoConstructor[] = [
  TrackerPreferenceDto,
  LanguagePreferenceDto,
  ResolutionPreferenceDto,
  VideoQualityPreferenceDto,
  SourcePreferenceDto,
  AudioQualityPreferenceDto,
  AudioSpatialPreferenceDto,
];

export const preferenceDtoMap: Record<
  PreferenceEnum,
  PreferenceDtoConstructor
> = {
  [PreferenceEnum.TRACKER]: TrackerPreferenceDto,
  [PreferenceEnum.LANGUAGE]: LanguagePreferenceDto,
  [PreferenceEnum.RESOLUTION]: ResolutionPreferenceDto,
  [PreferenceEnum.VIDEO_QUALITY]: VideoQualityPreferenceDto,
  [PreferenceEnum.SOURCE]: SourcePreferenceDto,
  [PreferenceEnum.AUDIO_QUALITY]: AudioQualityPreferenceDto,
  [PreferenceEnum.AUDIO_SPATIAL]: AudioSpatialPreferenceDto,
};
