import { DialogEnum, useDialogsStore } from '@/store/dialogs-store'

import { Dialog, DialogContent } from '../ui/dialog'
import { AddTrackerContent } from './add-tracker-content'
import { AddUserContent } from './add-user-content'
import { ChangePasswordContent } from './change-password-content'
import { ChangeUsernameContent } from './change-username-content'

export function DialogsRoot() {
  const { open, options, handleClose } = useDialogsStore()

  return (
    <Dialog open={open}>
      <DialogContent
        className="sm:max-w-[425px]"
        showCloseButton={false}
        onEscapeKeyDown={handleClose}
      >
        {options?.dialog === DialogEnum.ADD_TRACKER && (
          <AddTrackerContent activeTrackers={options.options.activeTrackers} />
        )}
        {options?.dialog === DialogEnum.CHANGE_USERNAME_DIALOG && (
          <ChangeUsernameContent user={options.options?.user} />
        )}
        {options?.dialog === DialogEnum.CHANGE_PASSWORD_DIALOG && (
          <ChangePasswordContent user={options.options?.user} />
        )}
        {options?.dialog === DialogEnum.ADD_USER && <AddUserContent />}
      </DialogContent>
    </Dialog>
  )
}
