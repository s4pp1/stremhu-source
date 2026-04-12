import { Expose } from 'class-transformer';

import { ContentTypeEnum } from '../enum/content-type.enum';
import { ManifestExtraDto } from './manifest-extra.dto';

export class ManifestCatalog {
  /** Tartalom típusa */
  @Expose()
  type: ContentTypeEnum;

  /** Katalógus azonosító */
  @Expose()
  id: string;

  /** Katalógus neve */
  @Expose()
  name: string;

  /** Extra szűrési paraméterek */
  @Expose()
  extra?: ManifestExtraDto[];
}
