import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { PreferenceValue } from './preference-value.type';

export type UserPreferenceToCreate = {
  preference: PreferenceEnum;
  preferred: PreferenceValue[];
  blocked: PreferenceValue[];
};
