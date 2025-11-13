import { useForm } from '@tanstack/react-form'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { ChangeUsernameDto, UserDto } from '@/client/app-client'
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
import { useChangeMeUsername } from '@/queries/me'
import { useChangeUsername } from '@/queries/users'
import { useDialogsStore } from '@/store/dialogs-store'

interface ChangeUsernameContentProps {
  user?: UserDto
}

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónéb kitöltése kötelező'),
})

export function ChangeUsernameContent(props: ChangeUsernameContentProps) {
  const { user } = props

  const { handleClose } = useDialogsStore()

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

  const form = useForm({
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
    <form name="change-username" className="grid gap-4" onSubmit={onSubmit}>
      <DialogHeader>
        <DialogTitle>{dialogConfig.title}</DialogTitle>
        <DialogDescription>{dialogConfig.description}</DialogDescription>
      </DialogHeader>
      <FieldGroup>
        <form.Field name="username">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Új felhasználónév</FieldLabel>
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
              Módosítás
            </Button>
          </DialogFooter>
        )}
      </form.Subscribe>
    </form>
  )
}
