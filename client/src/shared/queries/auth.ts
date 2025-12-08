import { useMutation, useQueryClient } from '@tanstack/react-query'

import { appClient } from '@/shared/lib/client'
import type { AuthLoginDto, CreateSetupDto } from '@/shared/lib/source-client'

import { getMe } from './me'
import { getSettingsStatus } from './settings-setup'

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AuthLoginDto) => {
      const me = await appClient.authentication.login(payload)
      return me
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getMe, staleTime: 0 })
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      await appClient.authentication.logout()
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getMe.queryKey })
      queryClient.clear()
    },
  })
}

export function useRegistration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: CreateSetupDto) => {
      await appClient.settings.create(payload)
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getMe, staleTime: 0 })
      await queryClient.fetchQuery({ ...getSettingsStatus, staleTime: 0 })
    },
  })
}
