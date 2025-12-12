import { useQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon } from 'lucide-react'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
import { assertExists } from '@/shared/lib/utils'
import { getTorrents } from '@/shared/queries/torrents'

import { Torrent } from '../-components/torrent'

export function Torrents() {
  const { data: torrents } = useQuery(getTorrents)
  assertExists(torrents)

  if (torrents.length === 0) {
    return (
      <Alert>
        <CircleCheckBigIcon />
        <AlertTitle>Nincs aktív torrent</AlertTitle>
        <AlertDescription>
          Amint elindítasz egy filmet vagy sorozatot, az ahhoz tartozó aktív
          torrentek itt jelennek meg.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid gap-4">
      {torrents.map((torrent) => (
        <Torrent key={torrent.infoHash} torrent={torrent} />
      ))}
    </div>
  )
}
