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
    host: z
      .string()
      .min(1, 'A domain megadása kötelező')
      .refine(
        (val) => !val.startsWith('http://') && !val.startsWith('https://'),
        {
          message: 'A protokoll (http/https) nem szerepelhet a domainben',
        },
      )
      .refine((val) => !/^\d{1,3}(\.\d{1,3}){3}/.test(val), {
        message: 'IP cím nem engedélyezett, csak domain',
      })
      .refine((val) => !val.includes(':'), {
        message: 'A port megadása nem engedélyezett',
      })
      .refine((val) => /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(\/.*)?$/.test(val), {
        message: 'Érvénytelen domain formátum',
      }),
  }),
])

export type NetworkAccessFormValues = z.infer<typeof networkAccessSchema>

export const createNetworkAccessSchema = (
  providers: { id: string; name: string; domainRegex: string }[],
) =>
  networkAccessSchema.superRefine((data, ctx) => {
    if (data.mode === 'auto') {
      const selectedProvider = providers.find((p) => p.id === data.provider)
      if (selectedProvider && selectedProvider.domainRegex) {
        const regex = new RegExp(selectedProvider.domainRegex)
        if (!regex.test(data.host)) {
          ctx.addIssue({
            code: 'custom',
            message: `Érvénytelen domain a(z) ${selectedProvider.name} szolgáltatóhoz`,
            path: ['host'],
          })
        }
      }
    }
  })
