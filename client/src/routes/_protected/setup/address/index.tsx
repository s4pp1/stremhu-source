import { createFileRoute, redirect } from '@tanstack/react-router'

import { getSettingsStatus } from '@/queries/settings-setup'

export const Route = createFileRoute('/_protected/setup/address/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient
    const { hasAddress } = await queryClient.ensureQueryData(getSettingsStatus)

    if (hasAddress) {
      throw redirect({ to: '/' })
    }
  },
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/setup/address/"!</div>
}
