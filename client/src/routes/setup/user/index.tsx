import { createFileRoute, redirect } from '@tanstack/react-router'
import _ from 'lodash'

import { UserRoleEnum } from '@/client/app-client'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useMetadataLabel } from '@/hooks/use-metadata-label'
import { getSettingsStatus } from '@/queries/settings-setup'

import { RegistrationForm } from './-components/registration-form'

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

function SetupUserRoute() {
  const { getUserRoleLabel } = useMetadataLabel()

  return (
    <div className="flex flex-col items-center py-10">
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
        <CardContent>
          <RegistrationForm />
        </CardContent>
      </Card>
    </div>
  )
}
