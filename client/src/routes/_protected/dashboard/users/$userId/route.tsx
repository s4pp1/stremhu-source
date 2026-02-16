import { useQuery } from '@tanstack/react-query'
import {
  Link,
  Outlet,
  createFileRoute,
  useParams,
} from '@tanstack/react-router'

import { Button } from '@/shared/components/ui/button'
import { CardTitle } from '@/shared/components/ui/card'
import { assertExists } from '@/shared/lib/utils'
import { getUser } from '@/shared/queries/users'

export const Route = createFileRoute('/_protected/dashboard/users/$userId')({
  component: UserSettingsLayout,
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

function UserSettingsLayout() {
  const { userId } = useParams({ from: '/_protected/dashboard/users/$userId' })
  const { data: user } = useQuery(getUser(userId))
  assertExists(user)

  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <CardTitle>{user.username}</CardTitle>
        <div className="flex gap-2 items-center bg-card border shadow-sm rounded-md p-1">
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/dashboard/users/$userId"
              params={{
                userId,
              }}
              activeOptions={{
                exact: true,
              }}
              activeProps={{ className: 'bg-background' }}
            >
              Fiók
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link
              to="/dashboard/users/$userId/preferences"
              params={{
                userId,
              }}
              activeProps={{ className: 'bg-background' }}
            >
              Preferenciák
            </Link>
          </Button>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
