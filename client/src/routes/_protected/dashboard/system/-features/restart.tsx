import { RefreshCwIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { parseApiError } from '@/shared/lib/utils'
import { useSystemRestart } from '@/shared/queries/system'

export function Restart() {
  const confirmDialog = useConfirmDialog()

  const { mutateAsync: restartSystem } = useSystemRestart()

  const handleRestartSystem: MouseEventHandler<HTMLButtonElement> = async (
    e,
  ) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: 'Biztos újra szeretnéd indítani az alkalmazást?',
      onConfirm: async () => {
        try {
          await restartSystem()
          toast.success(
            'Az újraindítás elindult! Töltsd újra az oldalt pár másodperc múlva!',
          )
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
        <CardTitle>Újraindítás</CardTitle>
        <CardDescription>
          Amennyiben problémát érzékelsz, lehetőséged van az alkalmazás
          újraindítására.
        </CardDescription>
        <CardAction>
          <Button
            size="icon-sm"
            variant="destructive"
            className="rounded-full"
            onClick={handleRestartSystem}
          >
            <RefreshCwIcon />
          </Button>
        </CardAction>
      </CardHeader>
    </Card>
  )
}
