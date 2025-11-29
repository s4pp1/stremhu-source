import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { ChangePasswordDto, UserDto } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAppForm } from '@/contexts/form-context'
import { useChangeMePassword } from '@/queries/me'
import { useChangePassword } from '@/queries/users'
import { useDialogsStore } from '@/store/dialogs-store'

interface ChangePasswordContentProps {
  user?: UserDto
}

const schema = z.object({
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

export function ChangePasswordContent(props: ChangePasswordContentProps) {
  const { user } = props

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
        dialogsStore.handleClose()
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
    dialogsStore.handleClose()
  }

  return (
    <DialogContent
      className="sm:max-w-md"
      showCloseButton={false}
      onEscapeKeyDown={dialogsStore.handleClose}
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
            <form.SubscribeButton type="submit">Módosítás</form.SubscribeButton>
          </DialogFooter>
        </form>
      </form.AppForm>
    </DialogContent>
  )
}
