import { useQuery } from '@tanstack/react-query'

import { getMetadata } from '@/shared/queries/metadata'

export function AppFooter() {
  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`A 'metadata' nincs a cache-ben.`)

  return (
    <div className="bg-card border-t shadow-sm">
      <div className="container mx-auto max-w-3xl p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:items-center text-muted-foreground text-sm">
          <p>StremHU Source · {metadata.version}</p>
          <div className="flex flex-col sm:items-end gap-1">
            <p>
              Hibát találtál?{' '}
              <a
                href="https://discord.gg/jRSPPY5XaN"
                target="_blank"
                className="link-primary underline"
              >
                Jelentsd Discordon
              </a>
            </p>
            <p>
              Elakadtál?{' '}
              <a
                href="https://stremhu.app"
                target="_blank"
                className="link-primary underline"
              >
                Nézd át a dokumentációt
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
