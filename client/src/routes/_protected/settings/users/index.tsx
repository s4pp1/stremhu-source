import { useQueries } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { PlusIcon, TrashIcon } from 'lucide-react'
import type { MouseEvent } from 'react'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
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
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { UserDto } from '@/shared/lib/source-client'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'
import { getUsers, useDeleteUser } from '@/shared/queries/users'

import { SETTINGS_USERS_NAME } from './route'

export const Route = createFileRoute('/_protected/settings/users/')({
  component: RouteComponent,
})

function RouteComponent() {
  const [{ data: users }, { data: me }] = useQueries({
    queries: [getUsers, getMe],
  })
  assertExists(users)
  assertExists(me)

  const confirmDialog = useConfirmDialog()
  const dialogs = useDialogs()

  const { getUserRoleLabel } = useMetadataLabel()
  const { mutateAsync: deleteUser } = useDeleteUser()

  const handleDeleteUser =
    (user: UserDto) => async (event: MouseEvent<HTMLButtonElement>) => {
      event.preventDefault()
      event.stopPropagation()

      await confirmDialog.confirm({
        title: `Biztos törölni szeretnéd?`,
        description: `"${user.username}" törlése végleges és nem lehetséges visszaállítani!`,
        onConfirm: async () => {
          await deleteUser(user.id)
        },
      })
    }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{SETTINGS_USERS_NAME}</CardTitle>
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
          <Link
            key={user.id}
            to="/settings/users/$userId"
            params={{ userId: user.id }}
          >
            <Item variant="muted">
              <ItemContent>
                <ItemTitle>
                  {user.username}
                  <span className="text-xs text-muted-foreground">
                    ({getUserRoleLabel(user.userRole)})
                  </span>
                </ItemTitle>
                <ItemDescription>{user.stremioToken}</ItemDescription>
              </ItemContent>
              {me.id !== user.id && (
                <ItemActions>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    className="rounded-full"
                    onClick={handleDeleteUser(user)}
                  >
                    <TrashIcon />
                  </Button>
                </ItemActions>
              )}
            </Item>
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
