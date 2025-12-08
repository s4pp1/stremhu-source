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
import type { ChangeUsernameDto } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useChangeMeUsername } from '@/shared/queries/me'
import { useChangeUsername } from '@/shared/queries/users'

import type { ChangeUsernameDialog } from './change-username.types'

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
})

export function ChangeUsernameDialog(
  dialog: OpenedDialog & ChangeUsernameDialog,
) {
  const { user } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: changeUsername } = useChangeUsername()
  const { mutateAsync: changeMeUsername } = useChangeMeUsername()

  const dialogConfig = {
    title: 'Felhasználónév módosítása',
    description:
      'Felhasználóneved módosítása után már ezzel tudsz majd újra bejelentkezni.',
    mutate: (payload: ChangeUsernameDto) => changeMeUsername(payload),
  }

  if (user) {
    dialogConfig.title = `${user.username} felhasználónevének módosítása`
    dialogConfig.description =
      'A felhasználónév módosítása után ezzel tud újra bejelentkezni.'
    dialogConfig.mutate = (payload: ChangeUsernameDto) =>
      changeUsername({ userId: user.id, payload })
  }

  const form = useAppForm({
    defaultValues: {
      username: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await dialogConfig.mutate(value)
        toast.success(`Sikeresen módosítva: ${value.username}`)
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
            name="change-username"
            className="grid gap-4"
            onSubmit={handleSubmit}
          >
            <DialogHeader>
              <DialogTitle>{dialogConfig.title}</DialogTitle>
              <DialogDescription>{dialogConfig.description}</DialogDescription>
            </DialogHeader>
            <form.AppField
              name="username"
              children={(field) => (
                <field.AppTextField label="Új felhasználónév" />
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
