import { createFileRoute } from '@tanstack/react-router'
import { TriangleAlertIcon } from 'lucide-react'

import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'

import { DownloadSpeed } from './-features/download-speed'
import { Torrents } from './-features/torrents'
import { UploadSpeed } from './-features/upload-speed'

export const Route = createFileRoute('/_protected/settings/torrent-client/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <DownloadSpeed />
          <UploadSpeed />
        </div>
        <Alert className="text-orange-400 *:data-[slot=alert-description]:text-orange-400 ">
          <TriangleAlertIcon />
          <AlertTitle className="line-clamp-2">
            200 Mbit/s felett a kliens jelentősen terhelheti a processzort.
          </AlertTitle>
        </Alert>
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle>Aktív torrentek</CardTitle>
          <CardDescription>
            Kövesd nyomon a torrentek statisztikáit és tűzd ki, ha nem
            szeretnéd, hogy autómatikusan törlődjenek.
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <Torrents />
        </CardContent>
      </Card>
    </div>
  )
}
