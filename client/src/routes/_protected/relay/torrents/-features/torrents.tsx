import { useSuspenseQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon, InfoIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
import { getTorrents } from '@/shared/queries/torrents'

import { Torrent } from '../-components/torrent'

export function Torrents() {
  const { data: torrents } = useSuspenseQuery(getTorrents)

  if (torrents.length === 0) {
    return (
      <Alert>
        <CircleCheckBigIcon />
        <AlertTitle><Trans>No active torrents</Trans></AlertTitle>
        <AlertDescription>
          <Trans>Torrents for the started media will appear here.</Trans>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid gap-4">
      {torrents.map((torrent) => (
        <Torrent key={torrent.infoHash} torrent={torrent} />
      ))}
      <Alert>
        <InfoIcon />
        <AlertTitle><Trans>Meaning of values shown under torrents</Trans></AlertTitle>
        <AlertDescription>
          <Trans>downloaded data | download speed | uploaded data | upload speed | total torrent size</Trans>
        </AlertDescription>
      </Alert>
    </div>
  )
}
