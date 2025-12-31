import { useQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon, InfoIcon } from 'lucide-react'

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
          Az elindított médiákhoz tartozó torrentek itt fognak megjelennie.
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
        <AlertTitle>Torrentek alatt látható értékek jelentése</AlertTitle>
        <AlertDescription>
          letöltött adat | letöltési sebesség | feltöltött adat | feltöltési
          sebesség | torrent teljes mérete
        </AlertDescription>
      </Alert>
    </div>
  )
}
