import { Link } from '@tanstack/react-router'
import { TrashIcon } from 'lucide-react'
import type { MouseEvent } from 'react'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type { UserDto } from '@/shared/lib/source/source-client'
import { useDeleteUser } from '@/shared/queries/users'

type UserItem = {
  user: UserDto
  deleteDisabled: boolean
}

export function UserItem(props: UserItem) {
  const { user, deleteDisabled } = props

  const confirmDialog = useConfirmDialog()

  const { getUserRoleLabel } = useMetadata()
  const { mutateAsync: deleteUser } = useDeleteUser()

  const handleDeleteUser = async (event: MouseEvent<HTMLButtonElement>) => {
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
    <Item asChild variant="muted" className="min-h-[66px]">
      <Link
        key={user.id}
        to="/dashboard/users/$userId"
        params={{ userId: user.id }}
      >
        <ItemContent>
          <ItemTitle>
            {user.username}
            <span className="text-xs text-muted-foreground">
              ({getUserRoleLabel(user.userRole)})
            </span>
          </ItemTitle>
        </ItemContent>
        {!deleteDisabled && (
          <ItemActions>
            <Button
              variant="destructive"
              size="icon-sm"
              className="rounded-full"
              onClick={handleDeleteUser}
            >
              <TrashIcon />
            </Button>
          </ItemActions>
        )}
      </Link>
    </Item>
  )
}
