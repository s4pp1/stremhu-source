import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import { assertExists } from '@/shared/lib/utils'
import { getUser } from '@/shared/queries/users'

import { UserProfile } from './-features/user-profile'

export const Route = createFileRoute('/_protected/dashboard/users/$userId/')({
  component: UserRoute,
})

function UserRoute() {
  const { userId } = useParams({ from: '/_protected/dashboard/users/$userId/' })

  const [{ data: user }] = useQueries({
    queries: [getUser(userId)],
  })
  assertExists(user)

  return (
    <div className="columns-1 md:columns-2 gap-4">
      <div className="break-inside-avoid mb-4">
        <UserProfile user={user} />
      </div>
    </div>
  )
}
