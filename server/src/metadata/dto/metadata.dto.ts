import { ApiExtraModels, ApiProperty, getSchemaPath } from '@nestjs/swagger';
import { Expose } from 'class-transformer';

import {
  PREFERENCE_META_SWAGGER_MODELS,
  PreferenceMetaDto,
} from './preference-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleMetaDto } from './user-role-meta.dto';

@ApiExtraModels(...PREFERENCE_META_SWAGGER_MODELS)
export class MetadataDto {
  /** Elérhető trackerek */
  @Expose()
  @ApiProperty({ type: TrackerMetaDto, isArray: true })
  trackers: TrackerMetaDto[];

  /** Elérhető felhasználói szerepkörök */
  @Expose()
  @ApiProperty({ type: UserRoleMetaDto, isArray: true })
  userRoles: UserRoleMetaDto[];

  /** Elérhető preferenciák listája */
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
