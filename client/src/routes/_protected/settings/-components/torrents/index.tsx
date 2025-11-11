import { useQuery } from '@tanstack/react-query'
import { CircleCheckBigIcon } from 'lucide-react'

import { DefaultLoading } from '@/components/default-loading'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { torrentsOptions } from '@/queries/torrents'

import { Torrent } from './torrent'

export function Torrents() {
  const { isPending, isError, data } = useQuery(torrentsOptions())

  if (isPending) {
    return <DefaultLoading message="Torrentek betöltése" />
  }

  if (isError) {
    return <div>Error</div>
  }

  if (data.length === 0) {
    return (
      <Alert>
        <CircleCheckBigIcon />
        <AlertTitle>Nincs aktív torrent</AlertTitle>
        <AlertDescription>
          Amint elindítasz egy filmet vagy sorozatot, itt jelennek meg az aktív
          torrentek.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {data.map((torrent) => (
        <Torrent key={torrent.infoHash} torrent={torrent} />
      ))}
    </div>
  )
}
