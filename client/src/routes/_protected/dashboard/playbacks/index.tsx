import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute, useSearch } from '@tanstack/react-router'
import { HistoryIcon, PlayIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'

import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { AppPagination } from '@/shared/components/ui/app-pagination'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { getPlaybackHistories, getPlaybacks } from '@/shared/queries/playbacks'

import { PlaybackItem } from './-components/playback-item'
import { DASHBOARD_PLAYBACKS_NAME } from './route'

export const Route = createFileRoute('/_protected/dashboard/playbacks/')({
  component: RouteComponent,
})

function RouteComponent() {
  const searchParams = useSearch({ from: '/_protected/dashboard/playbacks/' })

  const [{ data: playbacks }, { data: playbackHistories }] = useSuspenseQueries(
    {
      queries: [getPlaybacks, getPlaybackHistories(searchParams)],
    },
  )

  return (
    <div className="grid gap-8">
      <Card>
        <CardHeader>
          <CardTitle><Trans>Active {DASHBOARD_PLAYBACKS_NAME.toLowerCase()}</Trans></CardTitle>
          <CardDescription>
            <Trans>Active playbacks and key details.</Trans>
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="grid gap-3">
          {playbacks.length === 0 ? (
            <Alert>
              <PlayIcon />
              <AlertTitle><Trans>No active playbacks</Trans></AlertTitle>
            </Alert>
          ) : (
            playbacks.map((playback) => (
              <PlaybackItem key={playback.playbackId} playback={playback} />
            ))
          )}
        </CardContent>
      </Card>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle><Trans>Playback history</Trans></CardTitle>
          <CardDescription>
            <Trans>History and details of started playbacks.</Trans>
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="grid gap-3">
          {playbackHistories.items.length === 0 ? (
            <Alert>
              <HistoryIcon />
              <AlertTitle><Trans>No playback history</Trans></AlertTitle>
            </Alert>
          ) : (
            playbackHistories.items.map((playbackHistory) => (
              <PlaybackItem
                key={playbackHistory.playbackId}
                playback={playbackHistory}
              />
            ))
          )}
        </CardContent>
        <CardFooter>
          <AppPagination
            limit={playbackHistories.size}
            page={playbackHistories.page}
            total={playbackHistories.total}
            makeLink={(nextPage) => ({
              to: '/dashboard/playbacks',
              search: (prev) => ({ ...prev, page: nextPage }),
            })}
          />
        </CardFooter>
      </Card>
    </div>
  )
}
