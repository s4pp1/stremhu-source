import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import { useLogin } from '@/shared/queries/auth'
import { getMe } from '@/shared/queries/me'

export const Route = createFileRoute('/login/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    const me = await queryClient.ensureQueryData(getMe)

    if (me !== null) {
      throw redirect({ to: '/' })
    }
  },
  component: LoginRoute,
})

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

function LoginRoute() {
  const navigate = useNavigate({ from: '/login' })

  const { mutateAsync: login } = useLogin()

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
    <form.AppForm>
      <form
        name="login"
        className="flex flex-col items-center py-10"
        onSubmit={onSubmit}
      >
        <Card className="w-sm">
          <CardHeader>
            <CardTitle>Bejelentkezés a fiókodba</CardTitle>
            <CardDescription>
              Add meg felhasználóneved és jelszavad a bejelentkezéshez
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <form.AppField
              name="username"
              children={(field) => (
                <field.AppTextField label="Felhasználónév" />
              )}
            />
            <form.AppField
              name="password"
              children={(field) => (
                <field.AppTextField label="Jelszó" type="password" />
              )}
            />
          </CardContent>
          <CardFooter className="grid gap-4">
            <form.SubscribeButton type="submit">
              Bejelentkezés
            </form.SubscribeButton>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
