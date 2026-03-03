import { useQueries } from '@tanstack/react-query'
import { createFileRoute, useParams } from '@tanstack/react-router'
import { CopyIcon } from 'lucide-react'

import { TokenRegenerate } from '@/features/token-regenerate/token-regenerate'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { useCopy } from '@/shared/hooks/use-copy'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import { assertExists } from '@/shared/lib/utils'
import { getUser, useRegenerateUserToken } from '@/shared/queries/users'

import { UserProfile } from './-features/user-profile'

export const Route = createFileRoute('/_protected/dashboard/users/$userId/')({
  component: UserRoute,
})

function UserRoute() {
  const { userId } = useParams({ from: '/_protected/dashboard/users/$userId/' })

  const [{ data: user }] = useQueries({
    queries: [getUser(userId)],
  })
  assertExists(user)

  const { stremio, nuvioUrl, kodiUrl } = useIntegrationDomain({
    token: user.token,
  })

  const { handleCopy } = useCopy()

  const { mutateAsync: regenerateUserToken } = useRegenerateUserToken()

  const handleRegenerateToken = async () => {
    await regenerateUserToken(user.id)
  }

  return (
    <div className="grid gap-8">
      <div className="columns-1 md:columns-2 gap-4">
        <div className="break-inside-avoid mb-4">
          <UserProfile user={user} />
        </div>
        <div className="break-inside-avoid mb-4">
          <TokenRegenerate onSubmit={handleRegenerateToken} />
        </div>
      </div>
      <Separator />
      <div className="grid md:grid-cols-2 gap-4">
        <Item variant="muted">
          <ItemContent>
            <ItemTitle>Stremio URL</ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => handleCopy(stremio.urlEndpoint)}
            >
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item>
        <Item variant="muted">
          <ItemContent>
            <ItemTitle>Nuvio URL</ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => handleCopy(nuvioUrl)}
            >
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item>
        <Item variant="muted">
          <ItemContent>
            <ItemTitle>Kodi URL</ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => handleCopy(kodiUrl)}
            >
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item>
      </div>
    </div>
  )
}
