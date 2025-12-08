import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { useAppForm } from '@/shared/contexts/form-context'
import type { ChangePasswordDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useChangeMePassword } from '@/shared/queries/me'
import { useChangePassword } from '@/shared/queries/users'

import type { ChangePasswordDialog } from './change-password.types'

const schema = z.object({
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

export function ChangePasswordDialog(
  dialog: OpenedDialog & ChangePasswordDialog,
) {
  const { user } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: changePassword } = useChangePassword()
  const { mutateAsync: changeMePassword } = useChangeMePassword()

  const dialogConfig = {
    title: 'Jelszó módosítása',
    description:
      'A jelszó módosítása után ezzel tudsz majd újra bejelentkezni.',
    mutate: (payload: ChangePasswordDto) => changeMePassword(payload),
  }

  if (user) {
    dialogConfig.description =
      'A jelszó módosítása után ezzel tud újra bejelentkezni.'
    dialogConfig.mutate = (payload: ChangePasswordDto) =>
      changePassword({ userId: user.id, payload })
  }

  const form = useAppForm({
    defaultValues: {
      password: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await dialogConfig.mutate(value)
        toast.success(`Jelszó sikeresen módosítva!`)
        dialogsStore.closeDialog(dialog.id)
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: FormEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.closeDialog(dialog.id)
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-md"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <form
            name="change-password"
            className="grid gap-4"
            onSubmit={handleSubmit}
          >
            <DialogHeader>
              <DialogTitle>{dialogConfig.title}</DialogTitle>
              <DialogDescription>{dialogConfig.description}</DialogDescription>
            </DialogHeader>
            <form.AppField
              name="password"
              children={(field) => (
                <field.AppTextField label="Új jelszó" type="password" />
              )}
            />
            <DialogFooter>
              <form.SubscribeButton variant="outline" onClick={handleClose}>
                Mégsem
              </form.SubscribeButton>
              <form.SubscribeButton type="submit">
                Módosítás
              </form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
