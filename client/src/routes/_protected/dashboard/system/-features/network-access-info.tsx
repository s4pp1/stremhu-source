import { useSuspenseQueries } from '@tanstack/react-query'
import { SettingsIcon } from 'lucide-react'

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
import { getNetworkSettings } from '@/shared/queries/network'
import { getSystemStatus } from '@/shared/queries/system'

export function NetworkAccessInfo() {
  const dialogs = useDialogs()

  const [{ data: systemStatus }, { data: networkSettings }] =
    useSuspenseQueries({
      queries: [getSystemStatus, getNetworkSettings],
    })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Elérési beállítások</CardTitle>
        <CardDescription>
          A kliensek elvárják a biztonságos domain alapú SSL tanúsítvánnyal
          rendelkező elérést.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Konfigurált domain</ItemTitle>
            <ItemDescription className="font-bold font-mono break-all">
              {systemStatus.appUrl}
            </ItemDescription>
          </ItemContent>
        </Item>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Konfiguráció</ItemTitle>
            <ItemDescription>
              Elérési beállítások módosítása, konfigurálása.
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() => dialogs.openDialog({ type: 'NETWORK_ACCESS' })}
            >
              <SettingsIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
