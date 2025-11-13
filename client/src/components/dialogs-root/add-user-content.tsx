import { useForm } from '@tanstack/react-form'
import { isEmpty } from 'lodash'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import {
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useAddUser } from '@/queries/users'
import { useDialogsStore } from '@/store/dialogs-store'

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string(),
})

export function AddUserContent() {
  const { handleClose } = useDialogsStore()

  const { mutateAsync: addUser } = useAddUser()

  const form = useForm({
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
        handleClose()
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

  const onClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    handleClose()
  }

  return (
    <form name="add-user" className="grid gap-4" onSubmit={onSubmit}>
      <DialogHeader>
        <DialogTitle>Új fiók létrehozása</DialogTitle>
        <DialogDescription>
          Jelszó nélküli fiók létrehozása is lehetséges! Az ilyen fiókkal nincs
          lehetőség az addon felületére bejelentkezni, de a Stremio csatlakozás
          működik.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup>
        <form.Field name="username">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Felhasználónév</FieldLabel>
              <Input
                id={field.name}
                name={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
      </FieldGroup>
      <FieldGroup>
        <form.Field name="password">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Jelszó</FieldLabel>
              <Input
                id={field.name}
                name={field.name}
                type="password"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
      </FieldGroup>
      <form.Subscribe selector={(state) => [state.isSubmitting]}>
        {([isSubmitting]) => (
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isSubmitting}
              onClick={onClose}
            >
              Mégsem
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Létrehozás
            </Button>
          </DialogFooter>
        )}
      </form.Subscribe>
    </form>
  )
}
