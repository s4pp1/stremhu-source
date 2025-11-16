import { useForm } from '@tanstack/react-form'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { ChangePasswordDto, UserDto } from '@/client/app-client'
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

  const { handleClose } = useDialogsStore()

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

  const form = useForm({
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
    <form name="change-password" className="grid gap-4" onSubmit={onSubmit}>
      <DialogHeader>
        <DialogTitle>{dialogConfig.title}</DialogTitle>
        <DialogDescription>{dialogConfig.description}</DialogDescription>
      </DialogHeader>
      <FieldGroup>
        <form.Field name="password">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Új jelszó</FieldLabel>
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
              Módosítás
            </Button>
          </DialogFooter>
        )}
      </form.Subscribe>
    </form>
  )
}
