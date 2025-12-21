import { useQuery } from '@tanstack/react-query'

import type {
  LanguageEnum,
  ResolutionEnum,
  TrackerEnum,
  UserRoleEnum,
} from '@/shared/lib/source-client'
import { getMetadata } from '@/shared/queries/metadata'

export function useMetadata() {
  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { languages, resolutions, trackers, userRoles } = metadata

  const getUserRoleLabel = (userRoleEnum: UserRoleEnum): string => {
    const found = userRoles.find((role) => role.value === userRoleEnum)
    return found!.label
  }

  const getLanguageLabel = (languageEnum: LanguageEnum): string => {
    const found = languages.find((language) => language.value === languageEnum)
    return found!.label
  }

  const getResolutionLabel = (resolutionEnum: ResolutionEnum): string => {
    const found = resolutions.find(
      (resolution) => resolution.value === resolutionEnum,
    )
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

  return {
    getUserRoleLabel,
    getLanguageLabel,
    getResolutionLabel,
    getTrackerLabel,
    getTrackerFullDownload,
  }
}
