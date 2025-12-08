import type { ComponentType } from 'react'
import { Fragment } from 'react/jsx-runtime'

import { AddTrackerDialog } from '@/features/add-tracker/add-tracker-dialog'
import { AddUserDialog } from '@/features/add-user/add-user-dialog'
import { ChangePasswordDialog } from '@/features/change-password/change-password-dialog'
import { ChangeUsernameDialog } from '@/features/change-username/change-username-dialog'
import { ConfirmDialog } from '@/features/confirm/confirm-dialog'
import { NetworkAccessDialog } from '@/features/network-access/network-access-dialog'
import { StremhuCatalogDialog } from '@/features/stremhu-catalog/stremhu-catalog-dialog'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'

type DialogComponentMap = {
  [K in OpenedDialog['type']]: ComponentType<Extract<OpenedDialog, { type: K }>>
}

const dialogComponents = {
  CONFIRM: ConfirmDialog,
  ADD_TRACKER: AddTrackerDialog,
  CHANGE_USERNAME: ChangeUsernameDialog,
  CHANGE_PASSWORD: ChangePasswordDialog,
  ADD_USER: AddUserDialog,
  NETWORK_ACCESS: NetworkAccessDialog,
  STREMHU_CATALOG: StremhuCatalogDialog,
} satisfies DialogComponentMap

export function Dialogs() {
  const { dialogs } = useDialogsStore()

  return dialogs.map((dialog) => {
    const DialogComponent = dialogComponents[dialog.type] as ComponentType<
      typeof dialog
    >

    return (
      <Fragment key={dialog.id}>
        <DialogComponent {...dialog} />
      </Fragment>
    )
  })
}
