import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  AudioQualityEnum,
  LanguageEnum,
  PreferenceEnum,
  ReorderPreferencesDto,
  ResolutionEnum,
  SourceEnum,
  TrackerEnum,
  VideoQualityEnum,
} from '../lib/source/source-client'
import {
  mePreferencesCreate,
  mePreferencesDelete,
  mePreferencesFind,
  mePreferencesFindOne,
  mePreferencesReorder,
  mePreferencesUpdate,
} from '../lib/source/source-client'
import type { PreferenceDto } from '../type/preference.dto'

export type PreferenceItemDto =
  | TrackerEnum[]
  | LanguageEnum[]
  | ResolutionEnum[]
  | VideoQualityEnum[]
  | SourceEnum[]
  | AudioQualityEnum[]

export const getMePreferences = queryOptions({
  queryKey: ['me', 'preferences'],
  queryFn: async () => {
    const response = await mePreferencesFind()
    return response
  },
})

export function useCreateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await mePreferencesCreate(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export const getMePreference = (preference: PreferenceEnum) =>
  queryOptions({
    queryKey: ['me', 'preferences', preference],
    queryFn: async () => {
      const response = await mePreferencesFindOne(preference)
      return response
    },
  })

export function useUpdateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await mePreferencesUpdate(payload.preference, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function useReorderMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ReorderPreferencesDto) => {
      await mePreferencesReorder(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}

export function useDeleteMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (preference: PreferenceEnum) => {
      await mePreferencesDelete(preference)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}
