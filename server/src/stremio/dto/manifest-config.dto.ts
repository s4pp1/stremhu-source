import { Expose } from 'class-transformer';

import { ManifestConfigTypeEnum } from '../enum/manifest-config-type.enum';

export class ManifestConfigDto {
  /** Konfigurációs kulcs */
  @Expose()
  key: string;

  /** Konfiguráció típusa */
  @Expose()
  type: ManifestConfigTypeEnum;

  /** Alapértelmezett érték */
  @Expose()
  default?: string;

  /** Megjelenített cím */
  @Expose()
  title?: string;

  /** Választható opciók */
  @Expose()
  options?: string[];

  /** Kötelező-e a megadása */
  @Expose()
  required?: string;
}
