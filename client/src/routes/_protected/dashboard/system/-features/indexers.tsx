import { useSuspenseQueries } from '@tanstack/react-query'
import { LogInIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { Trans } from '@lingui/react/macro'

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
import { getIndexerDefinitions, getIndexers } from '@/shared/queries/indexers'

import { IndexerItem } from '../-components/indexer-item'

export function Indexers() {
  const [{ data: indexers }, { data: indexerDefinitions }] = useSuspenseQueries(
    {
      queries: [getIndexers, getIndexerDefinitions],
    },
  )

  const dialogs = useDialogs()

  const renderLogin = indexers.length < indexerDefinitions.length

  const handleLogin: MouseEventHandler<HTMLButtonElement> = (e) => {
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
        <CardTitle><Trans>Trackers</Trans></CardTitle>
        <CardDescription>
          <Trans>Manage and configure your tracker logins.</Trans>
        </CardDescription>
        {renderLogin && (
          <CardAction>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={handleLogin}
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
              <EmptyTitle><Trans>Log in!</Trans></EmptyTitle>
              <EmptyDescription>
                <Trans>To use StremHU Source, you must log in to at least one tracker!</Trans>
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleLogin}>
                  <LogInIcon />
                  <Trans>Login</Trans>
                </Button>
              </div>
            </EmptyContent>
          </Empty>
        )}
      </CardContent>
    </Card>
  )
}
