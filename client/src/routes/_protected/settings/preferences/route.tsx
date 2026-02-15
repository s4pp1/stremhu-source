import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getMePreferences } from '@/shared/queries/me-preferences'

export const SETTINGS_PREFERENCES_NAME = 'Preferenciák'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/preferences')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([context.queryClient.ensureQueryData(getMePreferences)])
  },
  loader: () => {
    return { breadcrumb: SETTINGS_PREFERENCES_NAME }
  },
})
