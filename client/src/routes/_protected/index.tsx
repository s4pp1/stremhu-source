import { Link, createFileRoute } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  LayoutDashboardIcon,
  ListVideoIcon,
  PlayIcon,
  ShieldUserIcon,
  UsersIcon,
} from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
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
import { Separator } from '@/shared/components/ui/separator'
import { useIsAdmin } from '@/shared/hooks/use-is-admin'
import { Trans } from '@lingui/react/macro'

import { Integration } from './-features/integration'
import { DASHBOARD_PLAYBACKS_NAME } from './dashboard/playbacks/route'
import { DASHBOARD_SYSTEM_NAME } from './dashboard/system/route'
import { DASHBOARD_USERS_NAME } from './dashboard/users/route'
import { SETTINGS_ACCOUNT_NAME } from './settings/account/route'
import { SETTINGS_PREFERENCES_NAME } from './settings/preferences/route'

export const Route = createFileRoute('/_protected/')({
  component: ProfileRoute,
})

function ProfileRoute() {
  const { isAdmin } = useIsAdmin()

  return (
    <div className="grid gap-8">
      <Integration />
      <Separator />
      <div className="grid gap-4">
        <CardHeader className="px-0">
          <CardTitle><Trans>Settings</Trans></CardTitle>
          <CardDescription>
            <Trans>You can change your account data, security settings, and torrent list preferences.</Trans>
          </CardDescription>
        </CardHeader>
        <div className="grid gap-4">
          <Item asChild variant="muted">
            <Link to="/settings/account">
              <ItemMedia variant="icon">
                <ShieldUserIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>
                  <Trans>{SETTINGS_ACCOUNT_NAME} - Login and security</Trans>
                </ItemTitle>
                <ItemDescription>
                  <Trans>Manage login details, password and security settings.</Trans>
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  className="rounded-full"
                  size="icon-sm"
                  variant="default"
                >
                  <ChevronRightIcon />
                </Button>
              </ItemActions>
            </Link>
          </Item>
          <Item asChild variant="muted">
            <Link to="/settings/preferences">
              <ItemMedia variant="icon">
                <ListVideoIcon />
              </ItemMedia>
              <ItemContent>
                <ItemTitle>
                  <Trans>{SETTINGS_PREFERENCES_NAME} - Torrent list customization</Trans>
                </ItemTitle>
                <ItemDescription>
                  <Trans>Configure what appears first in the results and what to exclude.</Trans>
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  className="rounded-full"
                  size="icon-sm"
                  variant="default"
                >
                  <ChevronRightIcon />
                </Button>
              </ItemActions>
            </Link>
          </Item>
        </div>
      </div>
      {isAdmin && (
        <>
          <Separator />
          <div className="grid gap-4">
            <CardHeader className="px-0">
              <CardTitle><Trans>Dashboard</Trans></CardTitle>
              <CardDescription>
                <Trans>System configuration and user management.</Trans>
              </CardDescription>
            </CardHeader>
            <div className="grid gap-4">
              <Item asChild variant="muted">
                <Link to="/dashboard/system">
                  <ItemMedia variant="icon">
                    <LayoutDashboardIcon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{DASHBOARD_SYSTEM_NAME}</ItemTitle>
                    <ItemDescription>
                      <Trans>Manage torrent sites, configure StremHU Source.</Trans>
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Button
                      className="rounded-full"
                      size="icon-sm"
                      variant="default"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </ItemActions>
                </Link>
              </Item>
              <Item asChild variant="muted">
                <Link to="/dashboard/users">
                  <ItemMedia variant="icon">
                    <UsersIcon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{DASHBOARD_USERS_NAME}</ItemTitle>
                    <ItemDescription>
                      <Trans>Create user accounts, manage and update profile data.</Trans>
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Button
                      className="rounded-full"
                      size="icon-sm"
                      variant="default"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </ItemActions>
                </Link>
              </Item>
              <Item asChild variant="muted">
                <Link to="/dashboard/playbacks">
                  <ItemMedia variant="icon">
                    <PlayIcon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{DASHBOARD_PLAYBACKS_NAME}</ItemTitle>
                    <ItemDescription>
                      <Trans>View current and past playbacks.</Trans>
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Button
                      className="rounded-full"
                      size="icon-sm"
                      variant="default"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </ItemActions>
                </Link>
              </Item>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
