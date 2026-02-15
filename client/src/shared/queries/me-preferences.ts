import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import { appClient } from '../lib/client'
import type {
  AudioPreferenceDto,
  AudioQualityEnum,
  LanguageEnum,
  LanguagePreferenceDto,
  PreferenceEnum,
  ResolutionEnum,
  ResolutionPreferenceDto,
  SourceEnum,
  SourcePreferenceDto,
  TrackerEnum,
  TrackerPreferenceDto,
  VideoPreferenceDto,
  VideoQualityEnum,
} from '../lib/source-client'

export type PreferenceDto =
  | TrackerPreferenceDto
  | LanguagePreferenceDto
  | ResolutionPreferenceDto
  | VideoPreferenceDto
  | SourcePreferenceDto
  | AudioPreferenceDto

export type PreferenceItemDto =
  | Array<TrackerEnum>
  | Array<LanguageEnum>
  | Array<ResolutionEnum>
  | Array<VideoQualityEnum>
  | Array<SourceEnum>
  | Array<AudioQualityEnum>

export const getMePreferences = queryOptions({
  queryKey: ['me', 'preferences'],
  queryFn: async () => {
    const response = await appClient.me.mePreferences()
    return response
  },
})

export function useCreateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await appClient.me.createMePreference(payload)
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
      const response = await appClient.me.mePreference(preference)
      return response
    },
  })

export function useUpdateMePreference() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: PreferenceDto) => {
      await appClient.me.updateMePreference(payload.preference, payload)
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
      await appClient.me.deleteMePreference(preference)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'preferences'] })
    },
  })
}
