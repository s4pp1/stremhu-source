import { Expose } from 'class-transformer';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ShortManifestResourceEnum } from '../enum/short-manifest-resource.enum';
import { FullManifestResourceDto } from './full-manifest-resource.dto';
import { ManifestBehaviorHintsDto } from './manifest-behavior-hints.dto';
import { ManifestCatalog } from './manifest-catalog.dto';
import { ManifestConfigDto } from './manifest-config.dto';

export class ManifestDto {
  /** Addon egyedi azonosítója */
  @Expose()
  id: string;

  /** Addon neve */
  @Expose()
  name: string;

  /** Addon leírása */
  @Expose()
  description: string;

  /** Addon verziója */
  @Expose()
  version: string;

  /** Támogatott erőforrások listája */
  @Expose()
  resources: Array<ShortManifestResourceEnum | FullManifestResourceDto>;

  /** Támogatott tartalom típusok */
  @Expose()
  types: ContentTypeEnum[];

  /** ID előtagok */
  @Expose()
  idPrefixes?: string[];

  /** Katalógusok listája */
  @Expose()
  catalogs: ManifestCatalog[];

  /** Külső addon katalógusok */
  @Expose()
  addonCatalogs?: ManifestCatalog[];

  /** Konfigurációs beállítások */
  @Expose()
  config?: ManifestConfigDto[];

  /** Háttérkép URL */
  @Expose()
  background?: string;

  /** Logo URL */
  @Expose()
  logo?: string;

  /** Kapcsolati email */
  @Expose()
  contactEmail?: string;

  /** Viselkedési tippek */
  @Expose()
  behaviorHints?: ManifestBehaviorHintsDto;
}
