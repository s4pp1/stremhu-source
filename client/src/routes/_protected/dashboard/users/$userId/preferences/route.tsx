import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getUserPreferences } from '@/shared/queries/user-preferences'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences',
)({
  component: RouteComponent,
  beforeLoad: async ({ context, params }) => {
    const { userId } = params

    await Promise.all([
      context.queryClient.ensureQueryData(getUserPreferences(userId)),
    ])
  },
})
