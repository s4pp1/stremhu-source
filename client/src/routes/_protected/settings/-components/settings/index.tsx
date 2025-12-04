import { NetworkAccessInfo } from './network-access-info'
import { StremhuCatalogInfo } from './stremhu-catalog-info'
import { Trackers } from './trackers'
import { WebTorrent } from './web-torrent'

export function Settings() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-2xl font-medium tracking-tight">Beállítások</h3>
      </div>
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <Trackers />
        </div>
        <div className="break-inside-avoid mb-4">
          <NetworkAccessInfo />
        </div>
        <div className="break-inside-avoid mb-4">
          <WebTorrent />
        </div>
        <div className="break-inside-avoid mb-4">
          <StremhuCatalogInfo />
        </div>
      </div>
    </div>
  )
}
