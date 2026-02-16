import { SourceEnum } from 'src/preference-items/enum/source.enum';

import { SourceOption } from '../type/source-option.type';

export const SOURCE_OPTIONS: SourceOption[] = [
  {
    value: SourceEnum.DISC_REMUX,
    label: 'Lemez (Remux - eredeti minőség)',
  },
  { value: SourceEnum.DISC_RIP, label: 'Lemez (Rip / újrakódolt)' },
  { value: SourceEnum.WEB_DL, label: 'Streaming (WEB-DL - eredeti)' },
  { value: SourceEnum.WEB_RIP, label: 'Streaming (WEBRip - újrakódolt)' },
  { value: SourceEnum.BROADCAST, label: 'TV (HDTV / közvetített)' },
  { value: SourceEnum.THEATRICAL, label: 'Mozis felvétel (CAM/TS/TC)' },
  { value: SourceEnum.UNKNOWN, label: 'Egyéb' },
];

export const SOURCE_TYPE_LABEL_MAP = SOURCE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<SourceEnum, string>,
);
