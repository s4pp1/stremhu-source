import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { ChangeUsernameDto, UserDto } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAppForm } from '@/contexts/form-context'
import { useChangeMeUsername } from '@/queries/me'
import { useChangeUsername } from '@/queries/users'
import { useDialogsStore } from '@/store/dialogs-store'

interface ChangeUsernameContentProps {
  user?: UserDto
}

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
})

export function ChangeUsernameContent(props: ChangeUsernameContentProps) {
  const { user } = props

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
            <form.SubscribeButton type="submit">Módosítás</form.SubscribeButton>
          </DialogFooter>
        </form>
      </form.AppForm>
    </DialogContent>
  )
}
