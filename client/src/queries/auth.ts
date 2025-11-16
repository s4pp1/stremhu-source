import { useMutation, useQueryClient } from '@tanstack/react-query'

import { appClient } from '@/client'
import type { AuthLoginDto, CreateSetupDto } from '@/client/app-client'

import { getMe } from './me'
import { getSettingsSetupStatus } from './settings-setup'

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AuthLoginDto) => {
      const me = await appClient.authentication.authControllerLogin(payload)
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
      await appClient.authentication.authControllerLogout()
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
      await appClient.settingsSetup.setupControllerCreate(payload)
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getSettingsSetupStatus, staleTime: 0 })
    },
  })
}
