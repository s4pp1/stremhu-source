import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/relay/')({
  beforeLoad: () => {
    throw redirect({ to: '/relay/torrents' })
  },
})
