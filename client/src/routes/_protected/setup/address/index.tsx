import { createFileRoute, redirect } from '@tanstack/react-router'

import { getSettings } from '@/queries/settings'
import { getSettingsStatus } from '@/queries/settings-setup'

import { NetworkAccess } from '../../../../components/network-access'

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
  return (
    <div className="flex flex-col items-center py-10">
      <div className="w-sm">
        <NetworkAccess />
      </div>
    </div>
  )
}
