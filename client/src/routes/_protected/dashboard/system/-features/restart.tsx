import { RefreshCwIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'
import { t } from '@lingui/core/macro'
import { Trans } from '@lingui/react/macro'

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
      title: t`Are you sure you want to restart the application?`,
      onConfirm: async () => {
        try {
          await restartSystem()
          toast.success(
            t`Restart initiated! Reload the page in a few seconds!`,
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
        <CardTitle><Trans>Restart</Trans></CardTitle>
        <CardDescription>
          <Trans>If you experience any issues, you can restart the application.</Trans>
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
