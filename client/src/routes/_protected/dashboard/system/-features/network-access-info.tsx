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
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { assertExists } from '@/shared/lib/utils'
import { getHealth } from '@/shared/queries/app'
import { getMetadata } from '@/shared/queries/metadata'

const networkCheckMap = {
  idle: {
    title: '🔎 Elérés ellenőrzése...',
  },
  pending: {
    title: '🔎 Elérés ellenőrzése...',
  },
  success: {
    title: '🟢 Elérés rendben',
  },
  error: {
    title: '🔴 Nem érhető el a megadott címen',
  },
}

export function NetworkAccessInfo() {
  const dialogs = useDialogs()

  const { data: metadata } = useQuery(getMetadata)
  assertExists(metadata)

  const { status: healthStatus } = useQuery(getHealth(metadata.endpoint))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Elérési adatok</CardTitle>
        <CardDescription>
          Itt láthatod, milyen címen éri el a Stremio a StremHU Source-ot, és
          hogy a kapcsolat rendben van-e.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>{networkCheckMap[healthStatus].title}</ItemTitle>
            <ItemDescription className="font-bold font-mono break-all">
              {metadata.endpoint}
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => dialogs.openDialog({ type: 'NETWORK_ACCESS' })}
            >
              <Edit2Icon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
