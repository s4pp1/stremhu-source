import { useQuery } from '@tanstack/react-query'

import { getMetadata } from '@/shared/queries/metadata'

export function AppFooter() {
  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`A 'metadata' nincs a cache-ben.`)

  return (
    <div className="bg-card border-t shadow-sm">
      <div className="container mx-auto max-w-3xl p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:items-center text-muted-foreground text-sm">
          <p>StremHU | Source · {metadata.version}</p>
          <p>
            Hibát találtál?{' '}
            <a
              href="https://discord.gg/jRSPPY5XaN"
              target="_blank"
              className="text-card-foreground underline underline-offset-4"
            >
              Jelentsd Discordon
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
