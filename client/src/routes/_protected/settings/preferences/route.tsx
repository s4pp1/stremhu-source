import { Outlet, createFileRoute } from '@tanstack/react-router'

export const SETTINGS_PREFERENCES_NAME = 'Preferenciák'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/preferences')({
  component: RouteComponent,
  loader: () => {
    return { breadcrumb: SETTINGS_PREFERENCES_NAME }
  },
})
