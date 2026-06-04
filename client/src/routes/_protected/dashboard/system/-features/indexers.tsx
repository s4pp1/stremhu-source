import { useQueries } from '@tanstack/react-query'
import { LogInIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/shared/components/ui/empty'
import { Separator } from '@/shared/components/ui/separator'
import { assertExists } from '@/shared/lib/utils'
import { getIndexers } from '@/shared/queries/indexers'

import { IndexerItem } from '../-components/indexer-item'

export function Indexers() {
  const [{ data: indexers }] = useQueries({
    queries: [getIndexers],
  })

  assertExists(indexers)

  const dialogs = useDialogs()

  const renderTrackerLogin = false

  const handleTrackerLogin: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogs.openDialog({
      type: 'ADD_INDEXER',
      options: {
        activeIndexerIds: indexers.map((indexer) => indexer.indexerId),
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trackerek</CardTitle>
        <CardDescription>
          Kezeld a tracker-eket és módosítsd a konfigurációit.
        </CardDescription>
        {renderTrackerLogin && (
          <CardAction>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={handleTrackerLogin}
            >
              <LogInIcon />
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-4">
        {indexers.map((indexer) => (
          <IndexerItem key={indexer.indexerId} indexer={indexer} />
        ))}
        {indexers.length === 0 && (
          <Empty className="p-2 md:p-2">
            <EmptyHeader>
              <EmptyTitle>Jelentkezz be!</EmptyTitle>
              <EmptyDescription>
                Az addon használatához, be kell jelentkezned legalább egy
                tracker-be!
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleTrackerLogin}>
                  <LogInIcon />
                  Bejelentkezés
                </Button>
              </div>
            </EmptyContent>
          </Empty>
        )}
      </CardContent>
    </Card>
  )
}
