export type ConfirmOptions = {
  title: React.ReactNode
  description?: React.ReactNode
  confirmText?: string
  cancelText?: string
  onConfirm?: () => Promise<void> | void
  onCancel?: () => Promise<void> | void
}

export type ConfirmDialog = {
  type: 'CONFIRM'
  resolve: (ok: boolean) => void
  handleConfirm: (dialogId: string) => Promise<void> | void
  handleCancel: (dialogId: string) => Promise<void> | void
  options: ConfirmOptions
}
