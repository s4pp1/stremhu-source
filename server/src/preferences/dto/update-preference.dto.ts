import { ApiProperty } from '@nestjs/swagger';
import { Equals, IsEnum, IsOptional } from 'class-validator';

import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { PreferenceEnum } from '../enum/preference.enum';

export class UpdateTrackerPreferenceDto {
  @Equals(PreferenceEnum.TRACKER)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.TRACKER;

  @IsOptional()
  @IsEnum(TrackerEnum, { each: true })
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  preferred?: TrackerEnum[];

  @IsOptional()
  @IsEnum(TrackerEnum, { each: true })
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  blocked?: TrackerEnum[];
}

export class UpdateLanguagePreferenceDto {
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.LANGUAGE;

  @IsOptional()
  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  preferred?: LanguageEnum[];

  @IsOptional()
  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum' })
  blocked?: LanguageEnum[];
}

export class UpdateResolutionPreferenceDto {
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.RESOLUTION;

  @IsOptional()
  @IsEnum(ResolutionEnum, { each: true })
  @ApiProperty({
    enum: ResolutionEnum,
    enumName: 'ResolutionEnum',
  })
  preferred?: ResolutionEnum[];

  @IsOptional()
  @IsEnum(ResolutionEnum, { each: true })
  @ApiProperty({
    enum: ResolutionEnum,
    enumName: 'ResolutionEnum',
  })
  blocked?: ResolutionEnum[];
}

export class UpdateVideoPreferenceDto {
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.VIDEO_QUALITY;

  @IsOptional()
  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
  })
  preferred?: VideoQualityEnum[];

  @IsOptional()
  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
  })
  blocked?: VideoQualityEnum[];
}

export class UpdateSourcePreferenceDto {
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.SOURCE;

  @IsOptional()
  @IsEnum(SourceEnum, { each: true })
  @ApiProperty({
    enum: SourceEnum,
    enumName: 'SourceEnum',
  })
  preferred?: SourceEnum[];

  @IsOptional()
  @IsEnum(SourceEnum, { each: true })
  @ApiProperty({
    enum: SourceEnum,
    enumName: 'SourceEnum',
  })
  blocked?: SourceEnum[];
}

export class UpdateAudioPreferenceDto {
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  preference: PreferenceEnum.AUDIO_QUALITY;

  @IsOptional()
  @IsEnum(AudioQualityEnum, { each: true })
  @ApiProperty({
    enum: AudioQualityEnum,
    enumName: 'AudioQualityEnum',
  })
  preferred?: AudioQualityEnum[];

  @IsOptional()
  @IsEnum(AudioQualityEnum, { each: true })
  @ApiProperty({
    enum: AudioQualityEnum,
    enumName: 'AudioQualityEnum',
  })
  blocked?: AudioQualityEnum[];
}
