import { Outlet, createFileRoute } from '@tanstack/react-router'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/settings/preferences/create')(
  {
    component: RouteComponent,
    loader: () => {
      return { breadcrumb: 'Hozzáadás' }
    },
  },
)
