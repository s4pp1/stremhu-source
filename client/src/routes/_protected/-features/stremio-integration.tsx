import { useQuery } from '@tanstack/react-query'
import {
  AppWindowIcon,
  CodeIcon,
  CopyIcon,
  ExternalLinkIcon,
  LinkIcon,
} from 'lucide-react'

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
  const { data: me } = useQuery(getMe)
  assertExists(me)

  const { appEndpoint, webEndpoint, urlEndpoint } = useIntegrationDomain({
    token: me.token,
  })

  const { handleCopy } = useCopy()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stremio</CardTitle>
        <CardDescription>
          Addon használata Stremio-val -
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
            <ItemTitle>Telepítés appban</ItemTitle>
            <ItemDescription>
              Megnyitja az alkalmazást és hozzáadja az addont.
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              asChild
            >
              <a href={appEndpoint} target="_blank">
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
            <ItemTitle>Telepítés weben</ItemTitle>
            <ItemDescription>
              A weboldalon jóváhagyással telepítheted az addont.
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              asChild
            >
              <a href={webEndpoint} target="_blank">
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
            <ItemTitle>URL másolása</ItemTitle>
            <ItemDescription>
              A kimásolt URL-t illeszd be az addonok közé.
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() => handleCopy(urlEndpoint)}
            >
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
