import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { sortBy } from 'lodash'
import { PlusIcon } from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'
import { assertExists } from '@/shared/lib/utils'
import { getMePreferences } from '@/shared/queries/me-preferences'

import { Preference } from './-components/preference'
import { SETTINGS_PREFERENCES_NAME } from './route'

export const Route = createFileRoute('/_protected/settings/preferences/')({
  component: RouteComponent,
})

function RouteComponent() {
  const { data: mePreferences } = useQuery(getMePreferences)
  assertExists(mePreferences)

  const preferredPreferences = sortBy(
    mePreferences.filter((preference) => preference.preferred.length > 0),
    'order',
  )
  const blockedPreferences = mePreferences.filter(
    (preference) =>
      preference.blocked.length !== 0 && preference.preferred.length === 0,
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>{SETTINGS_PREFERENCES_NAME}</CardTitle>
        <CardDescription>
          Szabd személyre a torrentlista rendezését. A seed alapú sorrenden
          felül megadhatsz extra preferenciákat és kizárásokat is, így a
          lejátszás indításakor mindig a számodra legjobb találatokat hozza
          előre.
        </CardDescription>
        <CardAction>
          <Button asChild size="icon-sm" className="rounded-full">
            <Link to="/settings/preferences/create">
              <PlusIcon />
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-6">
        <div className="grid gap-4">
          {preferredPreferences.map((preference) => (
            <Preference key={preference.preference} preference={preference} />
          ))}
        </div>
        <Separator />
        <div className="grid gap-4">
          {blockedPreferences.map((preference) => (
            <Preference key={preference.preference} preference={preference} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
