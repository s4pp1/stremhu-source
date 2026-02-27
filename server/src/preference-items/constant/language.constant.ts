import { LanguageEnum } from '../enum/language.enum';
import { LanguageOption } from '../type/language-option.type';

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  { label: 'magyar', value: LanguageEnum.HU },
  { label: 'angol', value: LanguageEnum.EN },
];

export const LANGUAGE_MAP = LANGUAGE_OPTIONS.reduce(
  (previousValue, value) => ({
    ...previousValue,
    [value.value]: value,
  }),
  {} as Record<LanguageEnum, LanguageOption>,
);
