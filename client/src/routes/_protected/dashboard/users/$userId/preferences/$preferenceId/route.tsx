import { Outlet, createFileRoute } from '@tanstack/react-router'
import { upperFirst } from 'lodash'
import * as z from 'zod'

import { getUserPreference } from '@/shared/queries/users'

const preferenceParamsSchema = z.object({
  preferenceId: z.string(),
})

const RouteComponent = () => <Outlet />

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/$preferenceId',
)({
  component: RouteComponent,
  params: {
    parse: (rawParams) => preferenceParamsSchema.parse(rawParams),
  },
  beforeLoad: async ({ context, params }) => {
    const { userId, preferenceId } = params

    const [userPreference] = await Promise.all([
      context.queryClient.ensureQueryData(
        getUserPreference(userId, preferenceId),
      ),
    ])

    return {
      userPreference,
    }
  },
  loader: ({ context }) => {
    const { userPreference } = context

    return {
      breadcrumb: `${upperFirst(userPreference.name)} configuration`,
    }
  },
})
