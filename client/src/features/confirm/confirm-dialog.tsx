import { useState } from 'react'
import type { MouseEventHandler } from 'react'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../shared/components/ui/alert-dialog'
import type { ConfirmDialog } from './confirm.types'

export function ConfirmDialog(dialog: OpenedDialog & ConfirmDialog) {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleConfirm: MouseEventHandler<HTMLButtonElement> = async (e) => {
    try {
      setIsSubmitting(true)

      e.preventDefault()
      e.stopPropagation()

      await dialog.handleConfirm(dialog.id)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel: MouseEventHandler<HTMLButtonElement> = async (e) => {
    try {
      setIsSubmitting(true)

      e.preventDefault()
      e.stopPropagation()

      await dialog.handleCancel(dialog.id)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AlertDialog open={dialog.open}>
      <AlertDialogContent className="md:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle>{dialog.options.title}</AlertDialogTitle>
          <AlertDialogDescription>
            {dialog.options.description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={isSubmitting}>
            {dialog.options.cancelText || 'Mégsem'}
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isSubmitting}>
            {dialog.options.confirmText || 'Megerősítés'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
