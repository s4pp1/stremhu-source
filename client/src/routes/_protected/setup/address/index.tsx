import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { getSettings } from '@/shared/queries/settings'
import { getSettingsStatus } from '@/shared/queries/settings-setup'

import {
  NETWORK_ACCESS_FORM_ID,
  NETWORK_ACCESS_HEADER,
  NetworkAccess,
} from '../../../../features/network-access/network-access-form'

export const Route = createFileRoute('/_protected/setup/address/')({
  beforeLoad: async ({ context }) => {
    const [{ hasAddress }] = await Promise.all([
      context.queryClient.ensureQueryData(getSettingsStatus),
      context.queryClient.ensureQueryData(getSettings),
    ])

    if (hasAddress) {
      throw redirect({ to: '/' })
    }
  },
  component: SetupAddressRoute,
})

function SetupAddressRoute() {
  const [isValid, setIsValid] = useState(false)
  const navigate = useNavigate({
    from: '/setup/address',
  })

  const handleSuccessOrSkip = () => {
    navigate({ to: '/settings' })
  }

  return (
    <div className="flex flex-col items-center py-10">
      <div className="w-md">
        <Card>
          <CardHeader>
            <CardTitle>{NETWORK_ACCESS_HEADER.TITLE}</CardTitle>
            <CardDescription>
              {NETWORK_ACCESS_HEADER.DESCRIPTION}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <NetworkAccess
              onSuccess={handleSuccessOrSkip}
              onSkip={handleSuccessOrSkip}
              onValidated={setIsValid}
            />
          </CardContent>
          <CardFooter className="gap-2 justify-end">
            <Button type="reset" variant="link" form={NETWORK_ACCESS_FORM_ID}>
              Kihagyás
            </Button>
            <Button
              type="submit"
              form={NETWORK_ACCESS_FORM_ID}
              disabled={!isValid}
            >
              Mentés
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
