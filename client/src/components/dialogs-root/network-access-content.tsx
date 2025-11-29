import { Button } from '@/components/ui/button'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useDialogsStore } from '@/store/dialogs-store'

import {
  NETWORK_ACCESS_FORM_ID,
  NETWORK_ACCESS_HEADER,
  NetworkAccess,
} from '../network-access'

export function NetworkAccessContent() {
  const dialogsStore = useDialogsStore()

  return (
    <DialogContent
      className="sm:max-w-md"
      showCloseButton={false}
      onEscapeKeyDown={dialogsStore.handleClose}
    >
      <DialogHeader>
        <DialogTitle>{NETWORK_ACCESS_HEADER.TITLE}</DialogTitle>
        <DialogDescription>
          {NETWORK_ACCESS_HEADER.DESCRIPTION}
        </DialogDescription>
      </DialogHeader>
      <NetworkAccess onSuccess={dialogsStore.handleClose} />
      <DialogFooter>
        <Button type="button" variant="link" onClick={dialogsStore.handleClose}>
          Mégsem
        </Button>
        <Button type="submit" form={NETWORK_ACCESS_FORM_ID}>
          Mentés
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
