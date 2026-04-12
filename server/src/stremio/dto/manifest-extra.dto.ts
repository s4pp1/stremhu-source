import { ExtraEnum } from '../enum/extra.enum';

export class ManifestExtraDto {
  /** Extra paraméter neve */
  name: ExtraEnum;

  /** Kötelező-e a paraméter */
  isRequired?: boolean;

  /** Választható opciók */
  options?: string[];

  /** Maximálisan választható opciók száma */
  optionsLimit?: number;
}
