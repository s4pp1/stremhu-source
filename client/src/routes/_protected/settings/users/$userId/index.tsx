import { useQuery } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import { assertExists } from '@/shared/lib/utils'
import { getUser } from '@/shared/queries/users'

export const Route = createFileRoute('/_protected/settings/users/$userId/')({
  component: UserRoute,
})

function UserRoute() {
  const { userId } = useParams({ from: '/_protected/settings/users/$userId' })

  const { data: user } = useQuery(getUser(userId))
  assertExists(user)

  const { getUserRoleLabel } = useMetadataLabel()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{user.username}</CardTitle>
        <CardDescription>{getUserRoleLabel(user.userRole)}</CardDescription>
      </CardHeader>
    </Card>
  )
}
