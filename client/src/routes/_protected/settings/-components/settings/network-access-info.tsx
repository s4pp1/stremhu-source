import { useQuery } from '@tanstack/react-query'
import { Edit2Icon } from 'lucide-react'

import { assertExists } from '@/common/assert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/components/ui/item'
import { getHealth } from '@/queries/app'
import { getMetadata } from '@/queries/metadata'
import { DialogEnum, useDialogs } from '@/store/dialogs-store'

const networkCheckMap = {
  idle: {
    title: 'Elérés ellenőrzése...',
  },
  pending: {
    title: 'Elérés ellenőrzése...',
  },
  success: {
    title: '🟢 Elérés rendben',
  },
  error: {
    title: '🔴 Nem érhető el a megadott címen',
  },
}

export function NetworkAccessInfo() {
  const { handleOpen } = useDialogs()

  const { data: metadata } = useQuery(getMetadata)
  assertExists(metadata)

  const { status: healthStatus } = useQuery(getHealth(metadata.endpoint))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Elérési adatok</CardTitle>
        <CardDescription>
          Itt láthatod, milyen címen éri el a Stremio a StremHU | Source-ot, és
          hogy a kapcsolat rendben van-e.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>{networkCheckMap[healthStatus].title}</ItemTitle>
            <ItemDescription>
              Elérési cím:{' '}
              <span className="font-bold font-mono">{metadata.endpoint}</span>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => handleOpen({ dialog: DialogEnum.NETWORK_ACCESS })}
            >
              <Edit2Icon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
