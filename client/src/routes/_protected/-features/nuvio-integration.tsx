import { useQuery } from '@tanstack/react-query'
import { CopyIcon, LinkIcon } from 'lucide-react'

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

export function NuvioIntegration() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  const { urlEndpoint } = useIntegrationDomain({
    token: me.token,
  })

  const { handleCopy } = useCopy()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nuvio</CardTitle>
        <CardDescription>
          Addon használata Nuvio-val -
          <a
            className="link-primary"
            href="https://nuvioapp.space/"
            target="_blank"
          >
            https://nuvioapp.space
          </a>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
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
