import { ApiExtraModels, ApiProperty, getSchemaPath } from '@nestjs/swagger';
import { IsArray, IsString } from 'class-validator';

import { HealthDto } from 'src/common/dto/health.dto';

import {
  PREFERENCE_META_SWAGGER_MODELS,
  PreferenceMetaDto,
} from './preference-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleDto } from './user-role.dto';

@ApiExtraModels(...PREFERENCE_META_SWAGGER_MODELS)
export class MetadataDto extends HealthDto {
  @IsArray()
  @ApiProperty({ type: UserRoleDto, isArray: true })
  userRoles: UserRoleDto[];

  @ApiProperty({
    type: 'array',
    items: {
      oneOf: PREFERENCE_META_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  preferences: PreferenceMetaDto[];

  @IsArray()
  @ApiProperty({ type: TrackerMetaDto, isArray: true })
  trackers: TrackerMetaDto[];

  @IsString()
  @ApiProperty()
  endpoint: string;
}
