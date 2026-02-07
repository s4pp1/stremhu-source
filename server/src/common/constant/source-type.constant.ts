import { SourceTypeEnum } from 'src/stremio/streams/enum/source-type.enum';

import { SourceTypeOption } from '../type/source-type-option.type';

export const SOURCE_TYPE_OPTIONS: SourceTypeOption[] = [
  {
    value: SourceTypeEnum.DISC_REMUX,
    label: 'Lemez (Remux - eredeti minőség)',
  },
  { value: SourceTypeEnum.DISC_RIP, label: 'Lemez (Rip / újrakódolt)' },
  { value: SourceTypeEnum.WEB_DL, label: 'Streaming (WEB-DL - eredeti)' },
  { value: SourceTypeEnum.WEB_RIP, label: 'Streaming (WEBRip - újrakódolt)' },
  { value: SourceTypeEnum.BROADCAST, label: 'TV (HDTV / közvetített)' },
  { value: SourceTypeEnum.THEATRICAL, label: 'Mozis felvétel (CAM/TS/TC)' },
  { value: SourceTypeEnum.UNKNOWN, label: 'Egyéb' },
];

export const SOURCE_TYPE_LABEL_MAP = SOURCE_TYPE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<SourceTypeEnum, string>,
);
