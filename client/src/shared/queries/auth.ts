import { useMutation, useQueryClient } from '@tanstack/react-query'

import type {
  LoginRequest,
  PairVerifyRequest,
  RegisterRequest,
} from '../lib/source/source-client'
import {
  authLogin,
  authLogout,
  authRegister,
  pairingVerify,
} from '../lib/source/source-client'
import { getMe } from './me'

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: LoginRequest) => {
      const response = await authLogin(payload)
      return response
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getMe(), staleTime: 0 })
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
      await queryClient.invalidateQueries({ queryKey: getMe().queryKey })
      queryClient.clear()
    },
  })
}

export function useRegistration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: RegisterRequest) => {
      await authRegister(payload)
    },
    onSuccess: async () => {
      await queryClient.fetchQuery({ ...getMe(), staleTime: 0 })
    },
  })
}

export function usePairVerify() {
  return useMutation({
    mutationFn: async (payload: PairVerifyRequest) => {
      const response = await pairingVerify(payload)
      return response
    },
  })
}
