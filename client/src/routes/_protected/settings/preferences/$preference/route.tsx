import { Outlet, createFileRoute } from '@tanstack/react-router'
import * as z from 'zod'

import { PreferenceEnum } from '@/shared/lib/source-client'
import { getMePreference } from '@/shared/queries/me-preferences'

const preferenceParamsSchema = z.object({
  preference: z.enum(PreferenceEnum),
})

const RouteComponent = () => <Outlet />

export const Route = createFileRoute(
  '/_protected/settings/preferences/$preference',
)({
  component: RouteComponent,
  params: {
    parse: (rawParams) => preferenceParamsSchema.parse(rawParams),
  },
  beforeLoad: async ({ context, params }) => {
    const { preference } = params

    const [mePreference] = await Promise.all([
      context.queryClient.ensureQueryData(getMePreference(preference)),
    ])

    return {
      mePreference,
    }
  },
  loader: ({ context }) => {
    return {
      breadcrumb: `${context.mePreference.preference}`,
    }
  },
})
