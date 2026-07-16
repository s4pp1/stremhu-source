import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { t } from '@lingui/core/macro'
import { Trans } from '@lingui/react/macro'
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
import { useRegistration } from '@/shared/queries/auth'
import { getSystemStatus } from '@/shared/queries/system'

export const Route = createFileRoute('/setup/user/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient
    const { configured } = await queryClient.ensureQueryData(getSystemStatus)

    if (configured) {
      throw redirect({ to: '/' })
    }
  },
  component: SetupUserRoute,
})

const schema = z.object({
  username: z.string().trim().nonempty(t`Username is required`),
  password: z.string().trim().nonempty(t`Password is required`),
})

function SetupUserRoute() {
  const navigate = useNavigate({ from: '/setup/user/' })

  const { mutateAsync: registration } = useRegistration()

  const form = useAppForm({
    defaultValues: { username: '', password: '' },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await registration(value)

        navigate({
          to: '/dashboard',
        })
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <form.AppForm>
      <form
        name="registration"
        className="py-10 flex flex-col items-center"
        onSubmit={onSubmit}
      >
        <Card className="w-sm">
          <CardHeader>
            <CardTitle><Trans>Create administrator account</Trans></CardTitle>
            <CardDescription>
              <Trans>Let's get started! Create the first account, which will have <span className="font-bold">Administrator</span> privileges.</Trans>
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <form.AppField
              name="username"
              children={(field) => (
                <field.AppTextField label={t`Username`} />
              )}
            />
            <form.AppField
              name="password"
              children={(field) => (
                <field.AppTextField label={t`Password`} type="password" />
              )}
            />
          </CardContent>
          <CardFooter className="grid gap-4">
            <form.SubscribeButton type="submit">
              <Trans>Create</Trans>
            </form.SubscribeButton>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
