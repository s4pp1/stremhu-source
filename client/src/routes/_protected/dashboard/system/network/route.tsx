import { Outlet, createFileRoute } from '@tanstack/react-router'

export const DASHBOARD_SYSTEM_NETWORK_NAME = 'Hálózat'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/dashboard/system/network')({
  component: RouteComponent,
  loader: () => {
    return { breadcrumb: DASHBOARD_SYSTEM_NETWORK_NAME }
  },
})
