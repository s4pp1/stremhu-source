import { Outlet, createFileRoute } from '@tanstack/react-router'
import * as z from 'zod'

import { PreferenceEnum } from '@/shared/lib/source-client'
import { getMePreference } from '@/shared/queries/me-preferences'
import { getMetadata } from '@/shared/queries/metadata'

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

    const [mePreference, metadata] = await Promise.all([
      context.queryClient.ensureQueryData(getMePreference(preference)),
      context.queryClient.ensureQueryData(getMetadata),
    ])

    return {
      mePreference,
      metadata,
    }
  },
  loader: ({ context }) => {
    const { metadata, mePreference } = context
    const preferenceName = metadata.preferences.find(
      (preference) => preference.value === mePreference.preference,
    )

    return {
      breadcrumb: `${preferenceName!.label}`,
    }
  },
})
