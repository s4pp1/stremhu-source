import { Expose } from 'class-transformer';

import { ExtraEnum } from '../enum/extra.enum';

export class ManifestExtraDto {
  /** Extra paraméter neve */
  @Expose()
  name: ExtraEnum;

  /** Kötelező-e a paraméter */
  @Expose()
  isRequired?: boolean;

  /** Választható opciók */
  @Expose()
  options?: string[];

  /** Maximálisan választható opciók száma */
  @Expose()
  optionsLimit?: number;
}
