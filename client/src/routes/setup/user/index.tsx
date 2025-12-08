import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import _ from 'lodash'
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
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import { UserRoleEnum } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useRegistration } from '@/shared/queries/auth'
import { getSettingsStatus } from '@/shared/queries/settings-setup'

export const Route = createFileRoute('/setup/user/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient
    const { hasAdminUser } =
      await queryClient.ensureQueryData(getSettingsStatus)

    if (hasAdminUser) {
      throw redirect({ to: '/' })
    }
  },
  component: SetupUserRoute,
})

const schema = z.object({
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

function SetupUserRoute() {
  const navigate = useNavigate({ from: '/setup/user' })

  const { getUserRoleLabel } = useMetadataLabel()
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
      <form name="registration" className="py-10" onSubmit={onSubmit}>
        <Card className="w-sm">
          <CardHeader>
            <CardTitle>
              {_.upperFirst(getUserRoleLabel(UserRoleEnum.ADMIN))} fiók
              létrehozása
            </CardTitle>
            <CardDescription>
              Kezdjük a beállítást! Hozd létre az első fiókot, ami "
              {getUserRoleLabel(UserRoleEnum.ADMIN)}" jogosultsággal fog
              rendelkezni.
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
              Létrehozás
            </form.SubscribeButton>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
