import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getUser } from '@/shared/queries/users'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/users/$userId')({
  component: RouteComponent,
  beforeLoad: async ({ context, params }) => {
    const { userId } = params

    const queryClient = context.queryClient

    const user = await queryClient.ensureQueryData(getUser(userId))

    return {
      user,
    }
  },
  loader: ({ context }) => {
    return {
      breadcrumb: `${context.user.username}`,
    }
  },
})
