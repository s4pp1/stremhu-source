import { useQuery } from '@tanstack/react-query'
import { PencilIcon, ShieldUserIcon, UserIcon, UserPenIcon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
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
import { useMetadata } from '@/shared/hooks/use-metadata'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

export function LoginAndSecurity() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  const { getUserRoleLabel } = useMetadata()
  const dialogs = useDialogs()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bejelentkezés és biztonság</CardTitle>
        <CardDescription>
          Módosíthatod felhasználóneved vagy jelszavadat
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>{me.username}</ItemTitle>
            <ItemDescription>
              {getUserRoleLabel(me.userRole)} jogosultság
            </ItemDescription>
          </ItemContent>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserPenIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Felhasználónév módosítása</ItemTitle>
            <ItemDescription>
              A felhasználónév módósítása után újra be kell jelentkezned
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
            <ItemTitle>Jelszó módosítása</ItemTitle>
            <ItemDescription>
              A jelszó módósítása után újra be kell jelentkezned
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
