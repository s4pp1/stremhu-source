import { Outlet, createFileRoute } from '@tanstack/react-router'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/attributes',
)({
  component: RouteComponent,
  loader: () => {
    return { breadcrumb: 'Attributes' }
  },
})
