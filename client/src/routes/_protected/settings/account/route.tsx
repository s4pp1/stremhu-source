import { Outlet, createFileRoute } from '@tanstack/react-router'

export const SETTINGS_ACCOUNT_NAME = 'Fiókom'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/account')({
  component: RouteComponent,
  loader: () => {
    return { breadcrumb: SETTINGS_ACCOUNT_NAME }
  },
})
