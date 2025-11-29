import { useNavigate } from '@tanstack/react-router'
import type { ComponentProps, FormEventHandler } from 'react'
import { toast } from 'sonner'
import z from 'zod/v4'

import { parseApiError } from '@/common/utils'
import { useAppForm } from '@/contexts/form-context'
import { cn } from '@/lib/utils'
import { useRegistration } from '@/queries/auth'

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

type DefaultValues = z.infer<typeof schema>

const defaultValues: DefaultValues = {
  username: '',
  password: '',
}

export function RegistrationForm({
  className,
  ...props
}: ComponentProps<'form'>) {
  const navigate = useNavigate()

  const { mutateAsync: registration } = useRegistration()

  const form = useAppForm({
    defaultValues,
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await registration(value)

        navigate({
          to: '/settings',
        })
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

  return (
    <form.AppForm>
      <form
        name="registration"
        onSubmit={onSubmit}
        className={cn('grid gap-4', className)}
        {...props}
      >
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
        <form.SubscribeButton type="submit">Létrehozás</form.SubscribeButton>
      </form>
    </form.AppForm>
  )
}
