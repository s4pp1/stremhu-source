import { ApiExtraModels, ApiProperty, getSchemaPath } from '@nestjs/swagger';
import { IsArray, IsString } from 'class-validator';

import { HealthDto } from 'src/common/dto/health.dto';

import {
  PREFERENCE_META_SWAGGER_MODELS,
  PreferenceMetaDto,
} from './preference-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleMetaDto } from './user-role-meta.dto';

@ApiExtraModels(...PREFERENCE_META_SWAGGER_MODELS)
export class MetadataDto extends HealthDto {
  /** Felhasználói szerepkörök listája */
  @IsArray()
  userRoles: UserRoleMetaDto[];

  /** Trackerek listája */
  @IsArray()
  trackers: TrackerMetaDto[];

  /** API végpont */
  @IsString()
  endpoint: string;

  /** Preferenciák listája (különböző típusú elemekkel) */
  @ApiProperty({
    type: 'array',
    items: {
      oneOf: PREFERENCE_META_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  preferences: PreferenceMetaDto[];
}
