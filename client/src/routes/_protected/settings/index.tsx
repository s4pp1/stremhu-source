import { createFileRoute } from '@tanstack/react-router'

import { getSettings } from '@/shared/queries/settings'
import { getTrackers } from '@/shared/queries/trackers'
import { getUsers } from '@/shared/queries/users'

import { Settings } from './-components/settings'
import { Torrents } from './-components/torrents'
import { Users } from './-components/users'

export const Route = createFileRoute('/_protected/settings/')({
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getSettings),
      context.queryClient.ensureQueryData(getTrackers),
      context.queryClient.ensureQueryData(getUsers),
    ])
  },
  component: SettingsRoute,
})

function SettingsRoute() {
  return (
    <div className="flex flex-col gap-6">
      <Settings />
      <Users />
      <div>
        <h3 className="text-2xl font-medium tracking-tight">Torrentek</h3>
      </div>
      <Torrents />
    </div>
  )
}
