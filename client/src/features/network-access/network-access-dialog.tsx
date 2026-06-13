import type { MouseEventHandler, SubmitEventHandler } from 'react'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'

import {
  NETWORK_ACCESS_FORM_ID,
  NETWORK_ACCESS_HEADER,
  useNetworkAccessForm,
} from './network-access-form'
import type { NetworkAccessDialog } from './network-access.types'
import { NetworkSelector } from './network-selector'
import { UrlConfiguration } from './url-configuration'

export function NetworkAccessDialog(
  dialog: OpenedDialog & NetworkAccessDialog,
) {
  const dialogsStore = useDialogsStore()

  const form = useNetworkAccessForm()

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.closeDialog(dialog.id)
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-lg"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <form
            id={NETWORK_ACCESS_FORM_ID}
            className="grid gap-4"
            onSubmit={handleSubmit}
          >
            <DialogHeader>
              <DialogTitle>{NETWORK_ACCESS_HEADER.TITLE}</DialogTitle>
              <DialogDescription>
                {NETWORK_ACCESS_HEADER.DESCRIPTION}
              </DialogDescription>
            </DialogHeader>
            <NetworkSelector form={form} />
            <UrlConfiguration form={form} />
            <DialogFooter>
              <form.SubscribeButton variant="outline" onClick={handleClose}>
                Mégsem
              </form.SubscribeButton>
              <form.Subscribe selector={(state) => [state.values.mode]}>
                {([mode]) => {
                  if (mode === 'none' || mode === 'local') return null

                  return (
                    <Button type="submit">
                      {mode === 'auto' ? 'Konfigurálás' : 'Mentés'}{' '}
                    </Button>
                  )
                }}
              </form.Subscribe>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
