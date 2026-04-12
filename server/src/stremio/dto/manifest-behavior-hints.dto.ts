import { Expose } from 'class-transformer';

export class ManifestBehaviorHintsDto {
  /** Felnőtt tartalom-e */
  @Expose()
  adult?: boolean;

  /** P2P alapú-e */
  @Expose()
  p2p?: boolean;

  /** Konfigurálható-e */
  @Expose()
  configurable?: boolean;

  /** Kötelező-e a konfiguráció */
  @Expose()
  configurationRequired?: boolean;
}
