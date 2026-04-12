import { Expose } from 'class-transformer';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';

export class FullManifestResourceDto {
  /** Erőforrás neve */
  @Expose()
  name: ShortManifestResourceEnum;

  /** Támogatott tartalom típusok */
  @Expose()
  types: ContentTypeEnum[];

  /** ID előtagok */
  @Expose()
  idPrefixes?: string[];
}
