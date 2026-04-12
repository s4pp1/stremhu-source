import { ApiExtraModels, ApiProperty, getSchemaPath } from '@nestjs/swagger';
import { Expose, Type } from 'class-transformer';
import { IsArray } from 'class-validator';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import {
  AudioQualityPreferenceMetaDto,
  AudioSpatialPreferenceMetaDto,
  LanguagePreferenceMetaDto,
  PREFERENCE_META_SWAGGER_MODELS,
  PreferenceMetaDto,
  ResolutionPreferenceMetaDto,
  SourcePreferenceMetaDto,
  TrackerPreferenceMetaDto,
  VideoQualityPreferenceMetaDto,
} from './preference-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleMetaDto } from './user-role-meta.dto';

@ApiExtraModels(...PREFERENCE_META_SWAGGER_MODELS)
export class MetadataDto {
  /** Elérhető trackerek */
  @IsArray()
  @Type(() => TrackerMetaDto)
  @Expose()
  @ApiProperty({ type: TrackerMetaDto, isArray: true })
  trackers: TrackerMetaDto[];

  /** Elérhető felhasználói szerepkörök */
  @IsArray()
  @Type(() => UserRoleMetaDto)
  @Expose()
  @ApiProperty({ type: UserRoleMetaDto, isArray: true })
  userRoles: UserRoleMetaDto[];

  /** Elérhető preferenciák listája */
  @IsArray()
  @Type(() => Object, {
    discriminator: {
      property: 'value',
      subTypes: [
        { name: PreferenceEnum.TRACKER, value: TrackerPreferenceMetaDto },
        { name: PreferenceEnum.LANGUAGE, value: LanguagePreferenceMetaDto },
        { name: PreferenceEnum.RESOLUTION, value: ResolutionPreferenceMetaDto },
        {
          name: PreferenceEnum.VIDEO_QUALITY,
          value: VideoQualityPreferenceMetaDto,
        },
        { name: PreferenceEnum.SOURCE, value: SourcePreferenceMetaDto },
        {
          name: PreferenceEnum.AUDIO_QUALITY,
          value: AudioQualityPreferenceMetaDto,
        },
        {
          name: PreferenceEnum.AUDIO_SPATIAL,
          value: AudioSpatialPreferenceMetaDto,
        },
      ],
    },
  })
  @Expose()
  @ApiProperty({
    type: 'array',
    items: {
      oneOf: PREFERENCE_META_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  preferences: PreferenceMetaDto[];

  /** Az alkalmazás verziója */
  @Expose()
  @ApiProperty()
  version: string;

  /** API végpont URL */
  @Expose()
  @ApiProperty()
  endpoint: string;
}
