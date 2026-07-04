import { useQuery, useSuspenseQueries } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { SettingsIcon } from 'lucide-react'

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
import { Separator } from '@/shared/components/ui/separator'
import { formatDateTime } from '@/shared/lib/utils'
import { getHealth } from '@/shared/queries/app'
import { getNetworkSettings } from '@/shared/queries/network'
import { getSystemStatus } from '@/shared/queries/system'

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
  const [{ data: systemStatus }, { data: networkSettings }] =
    useSuspenseQueries({
      queries: [getSystemStatus, getNetworkSettings],
    })

  const { status: healthStatus } = useQuery(getHealth(systemStatus.appUrl))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hálózati elérés</CardTitle>
        <CardDescription>
          Hálózati eléréssel kapcsolatos információk
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2">
          <Item variant="default" className="p-0">
            <ItemContent>
              <ItemTitle>{networkCheckMap[healthStatus].title}</ItemTitle>
              <ItemDescription className="font-bold font-mono break-all">
                {systemStatus.appUrl}
              </ItemDescription>
            </ItemContent>
          </Item>
          {networkSettings.mode === 'auto' && (
            <>
              <Item className="p-0">
                <ItemContent>
                  <ItemTitle>Tanúsítvány lejárata / frissítése</ItemTitle>
                  <ItemDescription className="font-bold font-mono break-all">
                    {formatDateTime(networkSettings.expiresAt)}
                  </ItemDescription>
                </ItemContent>
              </Item>
              <Item className="p-0">
                <ItemContent>
                  <ItemTitle>Utolsó IP szinkronizáció</ItemTitle>
                  <ItemDescription className="font-bold font-mono break-all">
                    {formatDateTime(networkSettings.lastIpSyncAt)}
                  </ItemDescription>
                </ItemContent>
              </Item>
            </>
          )}
        </div>
        <Separator />
        {systemStatus.isReverseProxy ? (
          <Item className="p-0">
            <ItemContent>
              <ItemTitle className="text-muted-foreground">
                A hálózati elérés környezeti változóban van beállítva.
              </ItemTitle>
            </ItemContent>
          </Item>
        ) : (
          <Item className="p-0">
            <ItemContent>
              <ItemTitle>
                Hálózati elérés frissítése vagy új konfiguráció alkalmazása.
              </ItemTitle>
            </ItemContent>
            <ItemActions>
              <Button size="icon-sm" className="rounded-full" asChild>
                <Link to="/dashboard/system/network">
                  <SettingsIcon />
                </Link>
              </Button>
            </ItemActions>
          </Item>
        )}
      </CardContent>
    </Card>
  )
}
