import { ApiProperty } from '@nestjs/swagger';
import { ClassConstructor } from 'class-transformer';
import { Equals, IsArray, IsString } from 'class-validator';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { AudioQualityDto } from './audio-quality.dto';
import { LanguageDto } from './language.dto';
import { ResolutionDto } from './resolution.dto';
import { SourceDto } from './source.dto';
import { VideoQualityDto } from './video-quality.dto';

export class LanguagePreferenceMetaDto {
  @Equals(PreferenceEnum.LANGUAGE)
  @ApiProperty({
    enum: [PreferenceEnum.LANGUAGE],
    example: PreferenceEnum.LANGUAGE,
  })
  value: PreferenceEnum.LANGUAGE;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: LanguageDto,
    isArray: true,
  })
  items: LanguageDto[];
}

export class ResolutionPreferenceMetaDto {
  @Equals(PreferenceEnum.RESOLUTION)
  @ApiProperty({
    enum: [PreferenceEnum.RESOLUTION],
    example: PreferenceEnum.RESOLUTION,
  })
  value: PreferenceEnum.RESOLUTION;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: ResolutionDto,
    isArray: true,
  })
  items: ResolutionDto[];
}

export class VideoQualityPreferenceMetaDto {
  @Equals(PreferenceEnum.VIDEO_QUALITY)
  @ApiProperty({
    enum: [PreferenceEnum.VIDEO_QUALITY],
    example: PreferenceEnum.VIDEO_QUALITY,
  })
  value: PreferenceEnum.VIDEO_QUALITY;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: VideoQualityDto,
    isArray: true,
  })
  items: VideoQualityDto[];
}

export class SourcePreferenceMetaDto {
  @Equals(PreferenceEnum.SOURCE)
  @ApiProperty({
    enum: [PreferenceEnum.SOURCE],
    example: PreferenceEnum.SOURCE,
  })
  value: PreferenceEnum.SOURCE;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: SourceDto,
    isArray: true,
  })
  items: SourceDto[];
}

export class AudioQualityPreferenceMetaDto {
  @Equals(PreferenceEnum.AUDIO_QUALITY)
  @ApiProperty({
    enum: [PreferenceEnum.AUDIO_QUALITY],
    example: PreferenceEnum.AUDIO_QUALITY,
  })
  value: PreferenceEnum.AUDIO_QUALITY;

  @IsString()
  @ApiProperty()
  label: string;

  @IsArray()
  @ApiProperty({
    type: AudioQualityDto,
    isArray: true,
  })
  items: AudioQualityDto[];
}

export type PreferenceMetaDto =
  | LanguagePreferenceMetaDto
  | ResolutionPreferenceMetaDto
  | VideoQualityPreferenceMetaDto
  | SourcePreferenceMetaDto
  | AudioQualityPreferenceMetaDto;

type PreferenceMetaDtoConstructor = ClassConstructor<PreferenceMetaDto>;

export const PREFERENCE_META_SWAGGER_MODELS: readonly PreferenceMetaDtoConstructor[] =
  [
    LanguagePreferenceMetaDto,
    ResolutionPreferenceMetaDto,
    VideoQualityPreferenceMetaDto,
    SourcePreferenceMetaDto,
    AudioQualityPreferenceMetaDto,
  ];
