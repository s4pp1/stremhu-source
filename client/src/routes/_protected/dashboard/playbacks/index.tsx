import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute, useSearch } from '@tanstack/react-router'
import { HistoryIcon, PlayIcon } from 'lucide-react'

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
          <CardTitle>Aktív {DASHBOARD_PLAYBACKS_NAME.toLowerCase()}</CardTitle>
          <CardDescription>
            Aktív lejátszások és a legfontosabb adatok.
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="grid gap-3">
          {playbacks.length === 0 ? (
            <Alert>
              <PlayIcon />
              <AlertTitle>Nincs aktív lejátszás</AlertTitle>
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
          <CardTitle>Lejátszási előzmények</CardTitle>
          <CardDescription>
            Elindított lejátszások története és részletes adatai.
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="grid gap-3">
          {playbackHistories.items.length === 0 ? (
            <Alert>
              <HistoryIcon />
              <AlertTitle>Nincs lejátszási előzmény</AlertTitle>
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
