import { ContentTypeEnum } from '../enum/content-type.enum';
import { ManifestExtraDto } from './manifest-extra.dto';

export class ManifestCatalog {
  /** Tartalom típusa */
  type: ContentTypeEnum;

  /** Katalógus azonosító */
  id: string;

  /** Katalógus neve */
  name: string;

  /** Extra szűrési paraméterek */
  extra?: ManifestExtraDto[];
}
