import { PreferenceEnum } from '../enum/preference.enum';
import { PreferenceOption } from '../type/preference-option.type';

export const PREFERENCE_OPTIONS: PreferenceOption[] = [
  {
    label: 'tracker',
    value: PreferenceEnum.TRACKER,
    description: 'A torrent tracker oldala.',
  },
  {
    label: 'nyelv',
    value: PreferenceEnum.LANGUAGE,
    description: 'A tartalom nyelve hang alapján.',
  },
  {
    label: 'felbontás',
    value: PreferenceEnum.RESOLUTION,
    description: 'A videó képmérete, felbontása.',
  },
  {
    label: 'forrás',
    value: PreferenceEnum.SOURCE,
    description: 'A kiadás forrástípusa / eredete.',
  },
  {
    label: 'képminőség',
    value: PreferenceEnum.VIDEO_QUALITY,
    description: 'A videó képi minőségi formátuma.',
  },
  {
    label: 'hangminőség',
    value: PreferenceEnum.AUDIO_QUALITY,
    description: 'A hangsáv formátuma / minősége',
  },
];

export const PREFERENCE_MAP = PREFERENCE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value,
  }),
  {} as Record<PreferenceEnum, PreferenceOption>,
);
