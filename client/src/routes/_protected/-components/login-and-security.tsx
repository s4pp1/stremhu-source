import { useQuery } from '@tanstack/react-query'
import { PencilIcon, ShieldUserIcon, UserIcon, UserPenIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item'
import { useMetadataLabel } from '@/hooks/use-metadata-label'
import { getMe } from '@/queries/me'
import { DialogEnum, useDialogs } from '@/store/dialogs-store'

export function LoginAndSecurity() {
  const { data: me } = useQuery(getMe)
  if (!me) throw new Error(`Nincs "me" a cache-ben`)

  const { getUserRoleLabel } = useMetadataLabel()
  const { handleOpen } = useDialogs()

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
                handleOpen({ dialog: DialogEnum.CHANGE_USERNAME_DIALOG })
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
                handleOpen({ dialog: DialogEnum.CHANGE_PASSWORD_DIALOG })
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
