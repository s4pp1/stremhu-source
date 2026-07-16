import { useQuery } from '@tanstack/react-query'
import { PencilIcon, ShieldUserIcon, UserIcon, UserPenIcon } from 'lucide-react'
import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Trans } from '@lingui/react/macro'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
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
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

export function LoginAndSecurity() {
  const { data: me } = useQuery(getMe())
  assertExists(me)

  const dialogs = useDialogs()

  return (
    <Card>
      <CardHeader>
        <CardTitle><Trans>Login and security</Trans></CardTitle>
        <CardDescription>
          <Trans>You can change your username or password</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>{me.username}</ItemTitle>
            <ItemDescription><Trans>{me.role.name} role</Trans></ItemDescription>
          </ItemContent>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserPenIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Change username</Trans></ItemTitle>
            <ItemDescription>
              <Trans>You will need to log in again after changing your username</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({
                  type: 'CHANGE_USERNAME',
                  options: {},
                })
              }
            >
              <PencilIcon />
            </Button>
          </ItemActions>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <ShieldUserIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Change password</Trans></ItemTitle>
            <ItemDescription>
              <Trans>You will need to log in again after changing your password</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({ type: 'CHANGE_PASSWORD', options: {} })
              }
            >
              <PencilIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
