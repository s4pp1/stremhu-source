import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';
import { FullManifestResourceDto } from './full-manifest-resource.dto';
import { ManifestBehaviorHintsDto } from './manifest-behavior-hints.dto';
import { ManifestCatalog } from './manifest-catalog.dto';
import { ManifestConfigDto } from './manifest-config.dto';

export class ManifestDto {
  /** Addon egyedi azonosítója */
  id: string;

  /** Addon neve */
  name: string;

  /** Addon leírása */
  description: string;

  /** Addon verziója */
  version: string;

  /** Támogatott erőforrások listája */
  resources: Array<ShortManifestResourceEnum | FullManifestResourceDto>;

  /** Támogatott tartalom típusok */
  types: ContentTypeEnum[];

  /** ID előtagok */
  idPrefixes?: string[];

  /** Katalógusok listája */
  catalogs: ManifestCatalog[];

  /** Külső addon katalógusok */
  addonCatalogs?: ManifestCatalog[];

  /** Konfigurációs beállítások */
  config?: ManifestConfigDto[];

  /** Háttérkép URL */
  background?: string;

  /** Logo URL */
  logo?: string;

  /** Kapcsolati email */
  contactEmail?: string;

  /** Viselkedési tippek */
  behaviorHints?: ManifestBehaviorHintsDto;
}
