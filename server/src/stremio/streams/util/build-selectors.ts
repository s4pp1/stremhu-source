import { isArray } from 'lodash';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { PreferenceValue } from 'src/users/preferences/type/preference-value.type';

export function buildSelectors(
  preference: PreferenceEnum,
  preferenceItems: PreferenceValue[],
) {
  const blockedSet = new Set(preferenceItems);

  const rankMap = Object.fromEntries(
    preferenceItems.map((preferenceItem, index) => [preferenceItem, index]),
  ) as Record<PreferenceValue, number>;

  return {
    filterToBlocked: (
      resolveUserPreferenceItem: (
        preference: PreferenceEnum,
      ) => PreferenceValue | PreferenceValue[],
    ) => {
      const preferenceItem = resolveUserPreferenceItem(preference);
      const items = isArray(preferenceItem) ? preferenceItem : [preferenceItem];

      return items.some((item) => blockedSet.has(item));
    },
    priorityIndex: (
      resolveUserPreferenceItem: (
        preference: PreferenceEnum,
      ) => PreferenceValue | PreferenceValue[],
    ) => {
      const preferenceItem = resolveUserPreferenceItem(preference);
      const items = isArray(preferenceItem) ? preferenceItem : [preferenceItem];

      const bestQualityRank = Math.min(
        ...items.map((item) => {
          const index = rankMap[item];
          return index ?? preferenceItems.length;
        }),
      );

      return bestQualityRank;
    },
  };
}
