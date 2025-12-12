import { Link } from '@tanstack/react-router'
import { CopyIcon, TrashIcon } from 'lucide-react'
import type { MouseEvent } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import { InputGroupButton } from '@/shared/components/ui/input-group'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { UserDto } from '@/shared/lib/source-client'
import { useDeleteUser } from '@/shared/queries/users'

type UserItem = {
  user: UserDto
  deleteDisabled: boolean
}

export function UserItem(props: UserItem) {
  const { user, deleteDisabled } = props

  const confirmDialog = useConfirmDialog()

  const { urlEndpoint } = useIntegrationDomain({
    stremioToken: user.stremioToken,
  })

  const { getUserRoleLabel } = useMetadataLabel()
  const { mutateAsync: deleteUser } = useDeleteUser()

  const handleCopyUrl = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()

    try {
      await navigator.clipboard.writeText(urlEndpoint)
      toast.success('URL kimásolva a vágólapra')
    } catch {
      toast.error('Másolás sikertelen')
    }
  }

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
          <div className="flex gap-2 items-center">
            {user.stremioToken}
            <Tooltip>
              <TooltipTrigger asChild>
                <InputGroupButton
                  variant="ghost"
                  size="icon-sm"
                  onClick={handleCopyUrl}
                >
                  <CopyIcon />
                </InputGroupButton>
              </TooltipTrigger>
              <TooltipContent>
                <p>Felhasználó manifest.json kimásolása addon telepítéshez</p>
              </TooltipContent>
            </Tooltip>
          </div>
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
      </Item>
    </Link>
  )
}
