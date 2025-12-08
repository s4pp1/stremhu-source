import { createFileRoute, redirect } from '@tanstack/react-router'
import _ from 'lodash'

import { getSettingsStatus } from '@/shared/queries/settings-setup'

export const Route = createFileRoute('/setup/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient
    const { hasAdminUser } =
      await queryClient.ensureQueryData(getSettingsStatus)

    if (!hasAdminUser) {
      throw redirect({ to: '/setup/user' })
    }

    throw redirect({ to: '/' })
  },
})
