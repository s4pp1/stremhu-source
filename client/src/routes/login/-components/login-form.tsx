import { useForm } from '@tanstack/react-form'
import { useNavigate } from '@tanstack/react-router'
import type { ComponentProps, FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { useLogin } from '@/queries/auth'

const schema = z.object({
  username: z.string(),
  password: z.string(),
})

type DefaultValues = z.infer<typeof schema>

const defaultValues: DefaultValues = {
  username: '',
  password: '',
}

export function LoginForm({ className, ...props }: ComponentProps<'form'>) {
  const navigate = useNavigate({ from: '/login' })

  const { mutateAsync: login } = useLogin()

  const form = useForm({
    defaultValues,
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await login(value)

        navigate({
          to: '/',
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
    <form
      name="login"
      onSubmit={onSubmit}
      className={cn('flex flex-col gap-6', className)}
      {...props}
    >
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
            </Field>
          )}
        </form.Field>
        <form.Field name="password">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Jelszó</FieldLabel>
              <Input
                type="password"
                id={field.name}
                name={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
            </Field>
          )}
        </form.Field>
        <form.Subscribe selector={(state) => [state.isSubmitting]}>
          {([isSubmitting]) => (
            <Button type="submit" disabled={isSubmitting}>
              Bejelentkezés
            </Button>
          )}
        </form.Subscribe>
      </FieldGroup>
    </form>
  )
}
