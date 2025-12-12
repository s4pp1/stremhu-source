import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getUsers } from '@/shared/queries/users'

export const SETTINGS_USERS_NAME = 'Felhasználók'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/users')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([context.queryClient.ensureQueryData(getUsers)])
  },
  loader: () => {
    return { breadcrumb: SETTINGS_USERS_NAME }
  },
})
