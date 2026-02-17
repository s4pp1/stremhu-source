import { useQuery } from '@tanstack/react-query'
import {
  AppWindowIcon,
  // CopyIcon,
  LinkIcon,
  PlusIcon,
} from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Input } from '@/shared/components/ui/input'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/shared/components/ui/popover'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

export function Integration() {
  const { data: me } = useQuery(getMe)
  assertExists(me)

  const { appEndpoint, webEndpoint, urlEndpoint } = useIntegrationDomain({
    token: me.token,
  })

  return (
    <div className="grid gap-4">
      <CardHeader className="px-0">
        <CardTitle>Integráció</CardTitle>
        <CardDescription>
          Telepítsd a StremHU Source-t akár több kliensbe.
        </CardDescription>
      </CardHeader>
      <div className="grid gap-3">
        {/* <Item variant="muted">
          <ItemContent>
            <ItemTitle>Stremio integráció</ItemTitle>
            <ItemDescription>Leírás</ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button size="icon-sm" className="rounded-full">
              <WorkflowIcon />
            </Button>
          </ItemActions>
        </Item>
        <Item variant="muted">
          <ItemContent>
            <ItemTitle>Nuvio integráció</ItemTitle>
            <ItemDescription>Leírás</ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button size="icon-sm" className="rounded-full">
              <WorkflowIcon />
            </Button>
            <Button size="icon-sm" className="rounded-full">
              <CopyIcon />
            </Button>
          </ItemActions>
        </Item> */}
        <Card>
          <CardHeader>
            <CardTitle>Stremio integráció</CardTitle>
            <CardDescription>
              Az addon használatához telepítened kell az addont Stremio fiókodba
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <Item variant="default" className="p-0">
              <ItemMedia variant="icon">
                <AppWindowIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>Telepítés a Stremio appban</ItemTitle>
                <ItemDescription>
                  Megnyitja a Stremio alkalmazást és hozzáadja az addont.
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
                    <PlusIcon />
                  </a>
                </Button>
              </ItemActions>
            </Item>
            <Item variant="default" className="p-0">
              <ItemMedia variant="icon">
                <LinkIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>Megnyitás a Stremio weben</ItemTitle>
                <ItemDescription>
                  A Stremio weboldalán jóváhagyással telepítheted az addont.
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
                    <PlusIcon />
                  </a>
                </Button>
              </ItemActions>
            </Item>
            <div className="flex justify-center">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="link"
                    className="text-sm font-mono tracking-tight"
                  >
                    Addon manuális telepítése
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="max-w-95 grid gap-4">
                  <p className="text-muted-foreground text-sm">
                    Másold ki az URL-t és add hozzá a Stremio alkalmazáshoz a
                    "Bővítmények" menüpontban.
                  </p>
                  <Input value={urlEndpoint} className="w-full" />
                </PopoverContent>
              </Popover>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
