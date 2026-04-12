import { ManifestConfigTypeEnum } from '../enum/manifest-config-type.enum';

export class ManifestConfigDto {
  /** Konfigurációs kulcs */
  key: string;

  /** Konfiguráció típusa */
  type: ManifestConfigTypeEnum;

  /** Alapértelmezett érték */
  default?: string;

  /** Megjelenített cím */
  title?: string;

  /** Választható opciók */
  options?: string[];

  /** Kötelező-e a megadása */
  required?: string;
}
