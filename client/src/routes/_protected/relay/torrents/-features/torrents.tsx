import { useQuery, useSuspenseQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon, InfoIcon } from 'lucide-react'
import { useMemo } from 'react'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
import { getStorageCleanupQueue, getTorrents } from '@/shared/queries/torrents'

import { Torrent } from '../-components/torrent'

export function Torrents() {
  const { data: torrents } = useSuspenseQuery(getTorrents)
  const { data: queue } = useQuery(getStorageCleanupQueue)

  const queueByInfoHash = useMemo(
    () =>
      new Map(
        (queue?.items ?? []).map((item) => [item.infoHash, item] as const),
      ),
    [queue],
  )

  if (torrents.length === 0) {
    return (
      <Alert>
        <CircleCheckBigIcon />
        <AlertTitle>Nincs aktív torrent</AlertTitle>
        <AlertDescription>
          Az elindított médiákhoz tartozó torrentek itt fognak megjelenni.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid gap-4">
      {torrents.map((torrent) => (
        <Torrent
          key={torrent.infoHash}
          torrent={torrent}
          queueItem={queueByInfoHash.get(torrent.infoHash)}
        />
      ))}
      <Alert>
        <InfoIcon />
        <AlertTitle>Torrentek alatt látható értékek jelentése</AlertTitle>
        <AlertDescription>
          letöltött adat | letöltési sebesség | feltöltött adat | feltöltési
          sebesség | torrent teljes mérete
        </AlertDescription>
      </Alert>
    </div>
  )
}
