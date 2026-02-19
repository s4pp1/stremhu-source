import { Outlet, createFileRoute } from '@tanstack/react-router'
import { upperFirst } from 'lodash'
import * as z from 'zod'

import { PreferenceEnum } from '@/shared/lib/source-client'
import { getMetadata } from '@/shared/queries/metadata'
import { getUserPreference } from '@/shared/queries/user-preferences'

const preferenceParamsSchema = z.object({
  preference: z.enum(PreferenceEnum),
})

const RouteComponent = () => <Outlet />

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/$preference',
)({
  component: RouteComponent,
  params: {
    parse: (rawParams) => preferenceParamsSchema.parse(rawParams),
  },
  beforeLoad: async ({ context, params }) => {
    const { userId, preference } = params

    const [userPreference, metadata] = await Promise.all([
      context.queryClient.ensureQueryData(
        getUserPreference(userId, preference),
      ),
      context.queryClient.ensureQueryData(getMetadata),
    ])

    return {
      userPreference,
      metadata,
    }
  },
  loader: ({ context }) => {
    const { metadata, userPreference } = context
    const preferenceName = metadata.preferences.find(
      (preference) => preference.value === userPreference.preference,
    )

    return {
      breadcrumb: `${upperFirst(preferenceName!.label)} konfigurációja`,
    }
  },
})
