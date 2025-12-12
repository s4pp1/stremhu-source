import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'

import {
  NETWORK_ACCESS_FORM_ID,
  NETWORK_ACCESS_HEADER,
  NetworkAccess,
} from './network-access-form'
import type { NetworkAccessDialog } from './network-access.types'

export function NetworkAccessDialog(
  dialog: OpenedDialog & NetworkAccessDialog,
) {
  const dialogsStore = useDialogsStore()

  return (
    <Dialog open={dialog.open}>
      <DialogContent
        className="md:max-w-md"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <DialogHeader>
          <DialogTitle>{NETWORK_ACCESS_HEADER.TITLE}</DialogTitle>
          <DialogDescription>
            {NETWORK_ACCESS_HEADER.DESCRIPTION}
          </DialogDescription>
        </DialogHeader>
        <NetworkAccess onSuccess={() => dialogsStore.closeDialog(dialog.id)} />
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => dialogsStore.closeDialog(dialog.id)}
          >
            Mégsem
          </Button>
          <Button type="submit" form={NETWORK_ACCESS_FORM_ID}>
            Mentés
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
