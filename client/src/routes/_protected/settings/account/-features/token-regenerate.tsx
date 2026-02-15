import { useQuery } from '@tanstack/react-query'
import { KeyRoundIcon, RotateCcwKeyIcon } from 'lucide-react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
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
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useRegenerateMeToken } from '@/shared/queries/me'

export function TokenRegenerate() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  const confirmDialog = useConfirmDialog()
  const { mutateAsync: regenerateMeToken } = useRegenerateMeToken()

  const handleChangeToken = async () => {
    await confirmDialog.confirm({
      title: 'Biztosan kérsz új kulcsot?',
      description:
        'Az új kulcs létrehozása után az integrált alkalmazásokban az addon nem fog működni amíg újra nem telepíted!',
      onConfirm: async () => {
        try {
          await regenerateMeToken()
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
        <CardTitle>Kulcs kezelése</CardTitle>
        <CardDescription>
          A StremHU Source ennek a kulcsnak a segítségével azonosítja a
          felhasználók az integrációnál.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <KeyRoundIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Új kulcs kérése</ItemTitle>
            <ItemDescription>A régi kulcs törlésre kerül!</ItemDescription>
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
