import { StremhuCatalogDialog } from '@/features/stremhu-catalog/stremhu-catalog-dialog'
import { DialogEnum, useDialogsStore } from '@/store/dialogs-store'

import { Dialog } from '../ui/dialog'
import { AddTrackerContent } from './add-tracker-content'
import { AddUserContent } from './add-user-content'
import { ChangePasswordContent } from './change-password-content'
import { ChangeUsernameContent } from './change-username-content'
import { NetworkAccessContent } from './network-access-content'

export function DialogsRoot() {
  const { open, options } = useDialogsStore()

  return (
    <Dialog open={open}>
      {options?.dialog === DialogEnum.ADD_TRACKER && (
        <AddTrackerContent activeTrackers={options.options.activeTrackers} />
      )}
      {options?.dialog === DialogEnum.CHANGE_USERNAME && (
        <ChangeUsernameContent user={options.options?.user} />
      )}
      {options?.dialog === DialogEnum.CHANGE_PASSWORD && (
        <ChangePasswordContent user={options.options?.user} />
      )}
      {options?.dialog === DialogEnum.ADD_USER && <AddUserContent />}
      {options?.dialog === DialogEnum.NETWORK_ACCESS && (
        <NetworkAccessContent />
      )}
      {options?.dialog === DialogEnum.STREMHU_CATALOG && (
        <StremhuCatalogDialog />
      )}
    </Dialog>
  )
}
