import { useQuery } from '@tanstack/react-query'
import {
  KeyRoundIcon,
  PencilIcon,
  RotateCcwKeyIcon,
  ShieldUserIcon,
  UserIcon,
  UserPenIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { parseApiError } from '@/common/utils'
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
import { Separator } from '@/components/ui/separator'
import { useMetadataLabel } from '@/hooks/use-metadata-label'
import { getMe, useChangeMeStremioToken } from '@/queries/me'
import { useConfirmDialog } from '@/store/confirm-dialog-store'
import { DialogEnum, useDialogs } from '@/store/dialogs-store'

export function LoginAndSecurity() {
  const { data: me } = useQuery(getMe)
  if (!me) throw new Error(`Nincs "me" a cache-ben`)

  const { getUserRoleLabel } = useMetadataLabel()
  const { handleOpen } = useDialogs()

  const confirmDialog = useConfirmDialog()
  const { mutateAsync: changeStremioToken } = useChangeMeStremioToken()

  const handleChangeToken = async () => {
    await confirmDialog({
      title: 'Biztos generálsz új kulcsot?',
      description:
        'A kulcs generálása után az addont újra kell telepítened a Stremio-ban.',
      onConfirm: async () => {
        try {
          await changeStremioToken()
          toast.success('Új kulcs generálása elkészült.')
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

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
              onClick={() => handleOpen({ dialog: DialogEnum.CHANGE_USERNAME })}
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
              onClick={() => handleOpen({ dialog: DialogEnum.CHANGE_PASSWORD })}
            >
              <PencilIcon />
            </Button>
          </ItemActions>
        </Item>
        <Separator />
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <KeyRoundIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Új kulcs generálása</ItemTitle>
            <ItemDescription>
              A régi kulcs törlésre kerül, így az addont újra kell telepíteni!
            </ItemDescription>
          </ItemContent>
          <ItemActions onClick={handleChangeToken}>
            <Button
              size="icon-sm"
              variant="destructive"
              className="rounded-full"
            >
              <RotateCcwKeyIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
