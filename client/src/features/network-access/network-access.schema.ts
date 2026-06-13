import * as z from 'zod'

import { NetworkConnectionEnum } from '@/shared/lib/source/source-client'

export const networkAccessSchema = z.discriminatedUnion('mode', [
  z.object({
    mode: z.literal('none'),
  }),
  z.object({
    mode: z.literal('local'),
  }),
  z.object({
    mode: z.literal('auto'),
    provider: z.string().min(1, 'A szolgáltató kiválasztása kötelező'),
    host: z.string().min(1, 'A domain megadása kötelező'),
    token: z.string().min(1, 'A token megadása kötelező'),
    email: z.email('Érvénytelen e-mail cím'),
    connection: z.enum(NetworkConnectionEnum),
  }),
  z.object({
    mode: z.literal('manual'),
    host: z.string().min(1, 'A domain megadása kötelező'),
  }),
])

export type NetworkAccessFormValues = z.infer<typeof networkAccessSchema>
