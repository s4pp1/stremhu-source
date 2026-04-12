import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';

export class FullManifestResourceDto {
  /** Erőforrás neve */
  name: ShortManifestResourceEnum;

  /** Támogatott tartalom típusok */
  types: ContentTypeEnum[];

  /** ID előtagok */
  idPrefixes?: string[];
}
