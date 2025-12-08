import { useQuery } from '@tanstack/react-query'
import { Edit2Icon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
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
  ItemTitle,
} from '@/shared/components/ui/item'
import { assertExists } from '@/shared/lib/utils'
import { getCatalogHealth } from '@/shared/queries/catalog'
import { getSettings } from '@/shared/queries/settings'

const networkCheckMap = {
  pending: {
    title: '🔎 Elérés ellenőrzése...',
  },
  success: {
    title: '🟢 StremHU | Catalog csatlakoztatva',
  },
  error: {
    title: '🔴 StremHU | Catalog nem érhető el vagy hibás a kulcs',
  },
}

export function StremhuCatalogInfo() {
  const dialogs = useDialogs()

  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const catalogConfigured = !!setting.catalogToken

  const { status: catalogHealth } = useQuery({
    ...getCatalogHealth,
    enabled: catalogConfigured,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>StremHU | Catalog integráció</CardTitle>
        <CardDescription>
          A StremHU | Catalog integráció lehetővé teszi, hogy a sorozatok
          speciális epizódjait is listázza a torrentek közzött.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>
              {catalogConfigured
                ? networkCheckMap[catalogHealth].title
                : '🔑 A StremHU | Catalog kulcs nincs megadva.'}
            </ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => dialogs.openDialog({ type: 'STREMHU_CATALOG' })}
            >
              <Edit2Icon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
      <CardContent className="flex justify-center">
        <a
          href="https://catalog.stremhu.app"
          target="_blank"
          className="text-sm font-mono tracking-tight hover:underline"
        >
          StremHU | Catalog
        </a>
      </CardContent>
    </Card>
  )
}
