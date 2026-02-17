import { useQuery } from '@tanstack/react-query'

import type {
  PreferenceEnum,
  TrackerEnum,
  UserRoleEnum,
} from '@/shared/lib/source-client'
import { getMetadata } from '@/shared/queries/metadata'

import type { PreferenceItemMeta } from '../type/preference-item-meta'
import type { PreferenceItemEnum } from '../type/preference-item.enum'

export function useMetadata() {
  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { preferences, trackers, userRoles } = metadata

  const getUserRoleLabel = (userRoleEnum: UserRoleEnum): string => {
    const found = userRoles.find((role) => role.value === userRoleEnum)
    return found!.label
  }

  const getTrackerLabel = (trackerEnum: TrackerEnum) => {
    const found = trackers.find((tracker) => tracker.value === trackerEnum)
    return found!.label
  }

  const getTrackerFullDownload = (trackerEnum: TrackerEnum) => {
    const found = trackers.find((tracker) => tracker.value === trackerEnum)
    return found!.requiresFullDownload
  }

  const getTrackerUrl = (trackerEnum: TrackerEnum) => {
    const found = trackers.find((tracker) => tracker.value === trackerEnum)
    return { url: found!.url, detailsPath: found!.detailsPath }
  }

  const getPreference = (preferenceEnum: PreferenceEnum) => {
    const found = preferences.find(
      (item) => (item.value as unknown as PreferenceEnum) === preferenceEnum,
    )
    return found!
  }

  const getPreferenceItem = (
    preferenceEnum: PreferenceEnum,
    preferenceItemEnum: PreferenceItemEnum,
  ): PreferenceItemMeta => {
    const preference = getPreference(preferenceEnum)

    const found = preference.items.find(
      (item) => item.value === preferenceItemEnum,
    )

    return found!
  }

  return {
    getUserRoleLabel,
    getTrackerLabel,
    getTrackerFullDownload,
    getTrackerUrl,
    getPreference,
    getPreferenceItem,
  }
}
