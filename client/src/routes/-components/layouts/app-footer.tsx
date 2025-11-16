import { useQuery } from '@tanstack/react-query'

import { getSettingsSetupStatus } from '@/queries/settings-setup'

export function AppFooter() {
  const { data } = useQuery(getSettingsSetupStatus)
  if (!data) throw new Error(`A 'data' nincs a cache-ben.`)

  return (
    <div className="bg-card border-t shadow-sm">
      <div className="container mx-auto max-w-3xl p-4">
        <div className="flex justify-between items-center text-muted-foreground text-sm">
          <p>StremHU | Source · v{data.version}</p>
          <p>
            Hibát találtál?{' '}
            <a
              href="https://github.com/s4pp1/stremhu-source"
              target="_blank"
              className="text-card-foreground underline underline-offset-4"
            >
              Jelentsd GitHub-on
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
