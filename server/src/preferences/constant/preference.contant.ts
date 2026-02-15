import { PreferenceEnum } from '../enum/preference.enum';
import { PreferenceOption } from '../type/preference-option.type';

export const PREFERENCE_OPTIONS: PreferenceOption[] = [
  { label: 'tracker', value: PreferenceEnum.TRACKER },
  { label: 'nyelv', value: PreferenceEnum.LANGUAGE },
  { label: 'felbontás', value: PreferenceEnum.RESOLUTION },
  { label: 'forrás', value: PreferenceEnum.SOURCE },
  { label: 'képminőség', value: PreferenceEnum.VIDEO_QUALITY },
  { label: 'hangminőség', value: PreferenceEnum.AUDIO_QUALITY },
];

export const PREFERENCE_LABEL_MAP = PREFERENCE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value.label,
  }),
  {} as Record<PreferenceEnum, string>,
);
