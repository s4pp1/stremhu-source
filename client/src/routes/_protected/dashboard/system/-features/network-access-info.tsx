import { useQuery, useSuspenseQueries } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { SettingsIcon } from 'lucide-react'
import { t } from '@lingui/core/macro'
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
  ItemTitle,
} from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { formatDateTime } from '@/shared/lib/utils'
import { getHealth } from '@/shared/queries/app'
import { getNetworkSettings } from '@/shared/queries/network'
import { getSystemStatus } from '@/shared/queries/system'



export function NetworkAccessInfo() {
  const [{ data: systemStatus }, { data: networkSettings }] =
    useSuspenseQueries({
      queries: [getSystemStatus, getNetworkSettings],
    })

  const { status: healthStatus } = useQuery(getHealth(systemStatus.appUrl))

  const networkCheckMap = {
    idle: {
      title: t`🔎 Checking access...`,
    },
    pending: {
      title: t`🔎 Checking access...`,
    },
    success: {
      title: t`🟢 Access OK`,
    },
    error: {
      title: t`🔴 Not accessible at the provided address`,
    },
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><Trans>Network access</Trans></CardTitle>
        <CardDescription>
          <Trans>Network access information</Trans>
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
                  <ItemTitle><Trans>Certificate expiration / renewal</Trans></ItemTitle>
                  <ItemDescription className="font-bold font-mono break-all">
                    {formatDateTime(networkSettings.expiresAt)}
                  </ItemDescription>
                </ItemContent>
              </Item>
              <Item className="p-0">
                <ItemContent>
                  <ItemTitle><Trans>Last IP sync</Trans></ItemTitle>
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
                <Trans>Network access is configured in environment variables.</Trans>
              </ItemTitle>
            </ItemContent>
          </Item>
        ) : (
          <Item className="p-0">
            <ItemContent>
              <ItemTitle>
                <Trans>Update network access or apply new configuration.</Trans>
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
