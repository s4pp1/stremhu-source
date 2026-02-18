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
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { parseApiError } from '@/shared/lib/utils'

type TokenRegenerateProps = {
  onSubmit: () => Promise<void>
}

export function TokenRegenerate(props: TokenRegenerateProps) {
  const { onSubmit } = props

  const confirmDialog = useConfirmDialog()

  const handleChangeToken = async () => {
    await confirmDialog.confirm({
      title: 'Biztosan kérsz új kulcsot?',
      description:
        'Az új kulcs létrehozása után az telepített alkalmazásokban az addon nem fog működni amíg újra nem telepíted!',
      onConfirm: async () => {
        try {
          await onSubmit()
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
          felhasználót az alkalmazásokban.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <KeyRoundIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Új kulcs kérése</ItemTitle>
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
