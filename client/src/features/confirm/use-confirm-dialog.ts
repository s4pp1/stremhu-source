import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'

import type { ConfirmOptions } from './confirm.types'

export function useConfirmDialog() {
  const confirm = (options: ConfirmOptions) => {
    const dialogsStore = useDialogsStore.getState()

    return new Promise<boolean>((resolve) => {
      dialogsStore.openDialog({
        type: 'CONFIRM',
        handleConfirm,
        handleCancel,
        resolve,
        options,
      })
    })
  }

  const handleConfirm = async (dialogId: string) => {
    const dialogsStore = useDialogsStore.getState()

    const activeDialog = dialogsStore.dialogs.find(
      (dialog) => dialog.id === dialogId,
    )

    if (activeDialog?.type === 'CONFIRM') {
      const action = activeDialog.options.onConfirm

      if (action) {
        await action()
      }

      activeDialog.resolve(true)

      dialogsStore.closeDialog(dialogId)
    }
  }

  const handleCancel = (dialogId: string) => {
    const dialogsStore = useDialogsStore.getState()

    const activeDialog = dialogsStore.dialogs.find(
      (dialog) => dialog.id === dialogId,
    )

    if (activeDialog?.type === 'CONFIRM') {
      activeDialog.resolve(false)

      dialogsStore.closeDialog(dialogId)
    }
  }

  return { confirm }
}
