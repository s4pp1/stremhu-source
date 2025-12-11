import { createFileRoute } from '@tanstack/react-router'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'

import { Torrents } from '../-components/torrents'
import { DownloadSpeed } from './-features/download-speed'
import { UploadSpeed } from './-features/upload-speed'

export const Route = createFileRoute('/_protected/settings/web-torrent/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <div className="grid gap-8">
      <div className="grid sm:grid-cols-2 gap-4">
        <DownloadSpeed />
        <UploadSpeed />
      </div>
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle>Aktív torrentek</CardTitle>
          <CardDescription>
            Az egyes torrentek alatt látható értékek sorrendben: a torrent
            teljes mérete, az eddig letöltött adat, az összes feltöltött adat és
            az aktuális feltöltési sebesség.
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
