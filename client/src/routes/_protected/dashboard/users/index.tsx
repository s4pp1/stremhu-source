import { useQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { PlusIcon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'
import { getUsers } from '@/shared/queries/users'

import { UserItem } from './-components/user-item'
import { DASHBOARD_USERS_NAME } from './route'

export const Route = createFileRoute('/_protected/dashboard/users/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [{ data: users }, { data: me }] = useQueries({
    queries: [getUsers, getMe],
  })
  assertExists(users)
  assertExists(me)

  const dialogs = useDialogs()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{DASHBOARD_USERS_NAME}</CardTitle>
        <CardDescription>
          Kezeld a felhasználókat, szerepköröket és hozzáféréseket.
        </CardDescription>
        <CardAction>
          <Button
            size="icon-sm"
            className="rounded-full"
            onClick={() => dialogs.openDialog({ type: 'ADD_USER' })}
          >
            <PlusIcon />
          </Button>
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-3">
        {users.map((user) => (
          <UserItem
            key={user.id}
            user={user}
            deleteDisabled={user.id === me.id}
          />
        ))}
      </CardContent>
    </Card>
  )
}
