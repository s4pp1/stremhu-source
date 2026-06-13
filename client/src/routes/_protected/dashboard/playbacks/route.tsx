import { Outlet, createFileRoute } from '@tanstack/react-router'
import * as z from 'zod'

import { getPlaybackHistories, getPlaybacks } from '@/shared/queries/playbacks'

export const DASHBOARD_PLAYBACKS_NAME = 'Lejátszások'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/dashboard/playbacks')({
  component: RouteComponent,
  validateSearch: z.object({
    page: z.number().int().positive().optional(),
    limit: z.number().int().positive().optional(),
  }),
  beforeLoad: async ({ context, search }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getPlaybacks),
      context.queryClient.ensureQueryData(getPlaybackHistories(search)),
    ])
  },
  loader: () => {
    return { breadcrumb: DASHBOARD_PLAYBACKS_NAME }
  },
})
