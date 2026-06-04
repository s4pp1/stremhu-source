import { v4 as uuidv4 } from 'uuid'
import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'

import type { AddIndexerDialog } from '@/features/add-indexer/add-indexer.types'
import type { AddUserDialog } from '@/features/add-user/add-user.types'
import type { ChangePasswordDialog } from '@/features/change-password/change-password.types'
import type { ChangeUsernameDialog } from '@/features/change-username/change-username.types'
import type { ConfirmDialog } from '@/features/confirm/confirm.types'
import type { EditIndexerDialog } from '@/features/edit-indexer/edit-indexer.type'
import type { NetworkAccessDialog } from '@/features/network-access/network-access.types'

type BaseOpenDialog = {
  onClose?: () => void
}

export type OpenDialog = BaseOpenDialog &
  (
    | ConfirmDialog
    | AddIndexerDialog
    | ChangeUsernameDialog
    | ChangePasswordDialog
    | AddUserDialog
    | NetworkAccessDialog
    | EditIndexerDialog
  )

type BaseDialogContent = {
  id: string
}

type BaserOpenedDialog = OpenDialog & BaseDialogContent

export type OpenedDialog = BaserOpenedDialog & {
  open: boolean
}

type DialogsStore = {
  dialogs: OpenedDialog[]
  openDialog: (dialog: OpenDialog) => string
  closeDialog: (id: string) => void
}

export const useDialogsStore = create<DialogsStore>((set, get) => ({
  dialogs: [],
  openDialog: (dialog) => {
    const id = uuidv4()

    set((state) => ({
      dialogs: [...state.dialogs, { id, open: true, ...dialog }],
    }))

    return id
  },
  closeDialog: (id) => {
    const { dialogs } = get()

    const foundDialog = dialogs.find((dialog) => dialog.id === id)
    if (foundDialog?.onClose) foundDialog.onClose()

    set((state) => ({
      dialogs: state.dialogs.map((dialog) =>
        dialog.id === id ? { ...dialog, open: false } : dialog,
      ),
    }))

    setTimeout(() => {
      set((state) => ({
        dialogs: state.dialogs.filter((dialog) => dialog.id !== id),
      }))
    }, 500)
  },
}))

export function useDialogs() {
  return useDialogsStore(
    useShallow((store) => ({
      openDialog: store.openDialog,
      closeDialog: store.closeDialog,
    })),
  )
}
