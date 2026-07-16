import { useQuery } from '@tanstack/react-query'
import {
  AppWindowIcon,
  CodeIcon,
  CopyIcon,
  ExternalLinkIcon,
  LinkIcon,
} from 'lucide-react'
import { Trans } from '@lingui/react/macro'

import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useCopy } from '@/shared/hooks/use-copy'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

export function StremioIntegration() {
  const { data: me } = useQuery(getMe())
  assertExists(me)

  const { stremio } = useIntegrationDomain({
    apiKey: me.apiKey,
  })

  const { handleCopy } = useCopy()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stremio</CardTitle>
        <CardDescription>
          <a
            className="link-primary"
            href="https://www.stremio.com"
            target="_blank"
          >
            https://www.stremio.com
          </a>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <AppWindowIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Install in app</Trans></ItemTitle>
            <ItemDescription>
              <Trans>Opens the application and adds the addon.</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              asChild
            >
              <a href={stremio.appEndpoint} target="_blank">
                <ExternalLinkIcon />
              </a>
            </Button>
          </ItemActions>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <CodeIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Install on web</Trans></ItemTitle>
            <ItemDescription>
              <Trans>You can install the addon with confirmation on the website.</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              asChild
            >
              <a href={stremio.webEndpoint} target="_blank">
                <ExternalLinkIcon />
              </a>
            </Button>
          </ItemActions>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <LinkIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle><Trans>Copy URL</Trans></ItemTitle>
            <ItemDescription>
              <Trans>Paste the copied URL into your addons.</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() => handleCopy(stremio.urlEndpoint)}
            >
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
