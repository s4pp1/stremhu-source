import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';

import { PreferenceMetaDto } from './preference-meta.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleMetaDto } from './user-role-meta.dto';

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
    isArray: true,
    oneOf: [
      { $ref: '#/components/schemas/TrackerPreferenceMetaDto' },
      { $ref: '#/components/schemas/LanguagePreferenceMetaDto' },
      { $ref: '#/components/schemas/ResolutionPreferenceMetaDto' },
      { $ref: '#/components/schemas/VideoQualityPreferenceMetaDto' },
      { $ref: '#/components/schemas/SourcePreferenceMetaDto' },
      { $ref: '#/components/schemas/AudioQualityPreferenceMetaDto' },
      { $ref: '#/components/schemas/AudioSpatialPreferenceMetaDto' },
    ],
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
