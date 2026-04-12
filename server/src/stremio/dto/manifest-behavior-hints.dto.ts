export class ManifestBehaviorHintsDto {
  /** Felnőtt tartalom-e */
  adult?: boolean;

  /** P2P alapú-e */
  p2p?: boolean;

  /** Konfigurálható-e */
  configurable?: boolean;

  /** Kötelező-e a konfiguráció */
  configurationRequired?: boolean;
}
