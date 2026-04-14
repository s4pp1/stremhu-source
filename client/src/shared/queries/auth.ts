import { useMutation, useQueryClient } from '@tanstack/react-query'

import type {
  AuthLoginDto,
  CreateSetupDto,
  PairVerifyRequestDto,
} from '../lib/source/source-client'
import {
  authLogin,
  authLogout,
  pairingsInternalVerify,
  setupCreate,
} from '../lib/source/source-client'
import { getMe } from './me'
import { getSettingsStatus } from './settings-setup'

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AuthLoginDto) => {
      const response = await authLogin(payload)
      return response
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
      await authLogout()
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
      await setupCreate(payload)
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getMe, staleTime: 0 })
      await queryClient.fetchQuery({ ...getSettingsStatus, staleTime: 0 })
    },
  })
}

export function usePairVerify() {
  return useMutation({
    mutationFn: async (payload: PairVerifyRequestDto) => {
      const response = await pairingsInternalVerify(payload)
      return response
    },
  })
}
