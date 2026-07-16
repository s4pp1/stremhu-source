import { useQuery } from '@tanstack/react-query'
import { Trans } from '@lingui/react/macro'

import { assertExists } from '@/shared/lib/utils'
import { getSystemStatus } from '@/shared/queries/system'

export function AppFooter() {
  const { data: systemStatus } = useQuery(getSystemStatus)
  assertExists(systemStatus)

  return (
    <div className="bg-card border-t shadow-sm">
      <div className="container mx-auto max-w-3xl p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:items-center text-muted-foreground text-sm">
          <div className="flex flex-col sm:items-start gap-1">
            <p>StremHU Source · {systemStatus.version}</p>
            <p>
              <Trans>If you like this project,</Trans>{' '}
              <a
                href="https://ko-fi.com/s4pp1"
                target="_blank"
                className="link-primary underline"
              >
                <Trans>support it on Ko-Fi</Trans>
              </a>
              !
            </p>
          </div>

          <div className="flex flex-col sm:items-end gap-1">
            <p>
              <Trans>Found a bug?</Trans>{' '}
              <a
                href="https://discord.gg/jRSPPY5XaN"
                target="_blank"
                className="link-primary underline"
              >
                <Trans>Report on Discord</Trans>
              </a>
            </p>
            <p>
              <Trans>Need help?</Trans>{' '}
              <a
                href="https://stremhu.app"
                target="_blank"
                className="link-primary underline"
              >
                <Trans>Read the documentation</Trans>
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
