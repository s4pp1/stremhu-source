import { isEmpty } from 'lodash'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAppForm } from '@/contexts/form-context'
import { useAddUser } from '@/queries/users'
import { useDialogsStore } from '@/store/dialogs-store'

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string(),
})

export function AddUserContent() {
  const dialogsStore = useDialogsStore()

  const { mutateAsync: addUser } = useAddUser()

  const form = useAppForm({
    defaultValues: {
      username: '',
      password: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await addUser({
          ...value,
          password: isEmpty(value.password) ? null : value.password,
        })
        toast.success(`${value.username} sikeresen létrehozva!`)
        dialogsStore.handleClose()
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: MouseEventHandler<HTMLButtonElement> = (e) => {
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
        <form name="add-user" className="grid gap-4" onSubmit={onSubmit}>
          <DialogHeader>
            <DialogTitle>Új fiók létrehozása</DialogTitle>
            <DialogDescription>
              Jelszó nélküli fiók létrehozása is lehetséges! Az ilyen fiókkal
              nincs lehetőség az addon felületére bejelentkezni, de a Stremio
              csatlakozás működik.
            </DialogDescription>
          </DialogHeader>
          <form.AppField
            name="username"
            children={(field) => <field.AppTextField label="Felhasználónév" />}
          />
          <form.AppField
            name="password"
            children={(field) => (
              <field.AppTextField label="Jelszó" type="password" />
            )}
          />

          <DialogFooter>
            <form.SubscribeButton variant="outline" onClick={handleClose}>
              Mégsem
            </form.SubscribeButton>
            <form.SubscribeButton type="submit">
              Létrehozás
            </form.SubscribeButton>
          </DialogFooter>
        </form>
      </form.AppForm>
    </DialogContent>
  )
}
