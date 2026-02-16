import { Preference } from 'src/preferences/type/preference.type';

export type UserPreference = Preference & {
  userId: string;
};
