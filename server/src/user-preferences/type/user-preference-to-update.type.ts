import { PreferenceValue } from './preference-value.type';

export type UserPreferenceToUpdate = {
  preferred?: PreferenceValue[];
  blocked?: PreferenceValue[];
};
