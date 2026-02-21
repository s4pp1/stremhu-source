import { ApiProperty } from '@nestjs/swagger';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';
import { FullManifestResourceDto } from './full-manifest-resource.dto';
import { ManifestBehaviorHintsDto } from './manifest-behavior-hints.dto';
import { ManifestCatalog } from './manifest-catalog.dto';
import { ManifestConfigDto } from './manifest-config.dto';

export class ManifestDto {
  @ApiProperty()
  id: string;

  @ApiProperty()
  name: string;

  @ApiProperty()
  description: string;

  @ApiProperty()
  version: string;

  @ApiProperty({
    type: Array<ShortManifestResourceEnum | FullManifestResourceDto>,
  })
  resources: Array<ShortManifestResourceEnum | FullManifestResourceDto>;

  @ApiProperty({ enum: ContentTypeEnum, isArray: true })
  types: ContentTypeEnum[];

  @ApiProperty()
  idPrefixes?: string[];

  @ApiProperty()
  catalogs: ManifestCatalog[];

  @ApiProperty()
  addonCatalogs?: ManifestCatalog[];

  @ApiProperty()
  config?: ManifestConfigDto[];

  @ApiProperty()
  background?: string;

  @ApiProperty()
  logo?: string;

  @ApiProperty()
  contactEmail?: string;

  @ApiProperty({ type: ManifestBehaviorHintsDto })
  behaviorHints?: ManifestBehaviorHintsDto;
}
