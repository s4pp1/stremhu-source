import { KeyRoundIcon, RotateCcwKeyIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Trans } from '@lingui/react/macro'
import { t } from '@lingui/core/macro'

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
      title: t`Are you sure you want to request a new key?`,
      description:
        t`After generating a new key, the addon will not work in the installed applications until you reinstall it!`,
      onConfirm: async () => {
        try {
          await onSubmit()
          toast.success(t`New key generation is complete.`)
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
        <CardTitle><Trans>Manage key</Trans></CardTitle>
        <CardDescription>
          <Trans>StremHU Source uses this key to identify the user in the applications.</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <KeyRoundIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Request a new key</Trans></ItemTitle>
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
