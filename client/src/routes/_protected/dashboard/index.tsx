import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/dashboard/')({
  beforeLoad: () => {
    throw redirect({ to: '/dashboard/system' })
  },
})
