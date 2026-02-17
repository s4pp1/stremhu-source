import type { DragEndEvent } from '@dnd-kit/core'
import { DndContext } from '@dnd-kit/core'
import {
  restrictToVerticalAxis,
  restrictToWindowEdges,
} from '@dnd-kit/modifiers'
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import type { LinkProps } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import { sortBy } from 'lodash'
import { GrabIcon, PlusIcon, SearchIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Fragment, useEffect, useMemo, useState } from 'react'

import { SETTINGS_PREFERENCES_NAME } from '@/routes/_protected/settings/preferences/route'
import { SortableWrapper } from '@/shared/components/sortable-wrapper'
import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
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
import { Separator } from '@/shared/components/ui/separator'
import type { PreferenceEnum } from '@/shared/lib/source-client'
import type { PreferenceDto } from '@/shared/type/preference.dto'

type PreferencesSectionProps = {
  preferences: Array<PreferenceDto>
  toCreateLink: LinkProps
  renderPreference: (preference: PreferenceDto) => ReactNode
  onReorder: (preferences: Array<PreferenceEnum>) => Promise<void>
}

export function PreferencesSection(props: PreferencesSectionProps) {
  const { preferences, toCreateLink, renderPreference, onReorder } = props

  const preferredPreferences = useMemo(
    () =>
      sortBy(
        preferences.filter((preference) => preference.preferred.length > 0),
        'order',
      ),
    [preferences],
  )
  const blockedPreferences = useMemo(
    () =>
      preferences.filter(
        (preference) =>
          preference.blocked.length !== 0 && preference.preferred.length === 0,
      ),
    [preferences],
  )

  const [items, setItems] = useState(preferredPreferences)

  useEffect(() => {
    setItems(preferredPreferences)
  }, [preferredPreferences])

  const handleDragEnd = async (event: DragEndEvent) => {
    const { over, active } = event
    if (!over || active.id === over.id) return

    const oldIndex = items.findIndex((item) => item.preference === active.id)
    const newIndex = items.findIndex((item) => item.preference === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(items, oldIndex, newIndex)
    setItems(reordered)

    await onReorder(reordered.map((item) => item.preference))
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{SETTINGS_PREFERENCES_NAME}</CardTitle>
        <CardDescription>
          Testreszabhatod, milyen torrentek kerüljenek előre a listában, és mit
          szeretnél kizárni. A preferált tulajdonságok a sorrendet javítják, a
          kizárások pedig kiszűrik a nem kívánt találatokat.
        </CardDescription>
        <CardAction>
          <Button asChild size="icon-sm" className="rounded-full">
            <Link {...toCreateLink}>
              <PlusIcon />
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-8">
        <div className="grid gap-4">
          <Item className="p-0">
            <ItemContent>
              <ItemTitle>Preferencia sorrend</ItemTitle>
              <ItemDescription>
                Preferált tulajdonsággal rendelkező szabályok esetén módosítható
                azok súlyozása a sorrend módosításával.
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <ItemMedia variant="icon" className="rounded-full">
                <GrabIcon />
              </ItemMedia>
            </ItemActions>
          </Item>
        </div>
        <DndContext
          onDragEnd={handleDragEnd}
          modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
        >
          <div className="grid gap-3">
            <SortableContext
              items={items.map(
                (preferredPreference) => preferredPreference.preference,
              )}
              strategy={verticalListSortingStrategy}
            >
              {items.map((preference) => (
                <SortableWrapper
                  key={preference.preference}
                  item={preference}
                  resolveId={(i) => i.preference}
                >
                  <Fragment key={preference.preference}>
                    {renderPreference(preference)}
                  </Fragment>
                </SortableWrapper>
              ))}
            </SortableContext>
            {items.length === 0 && (
              <Alert>
                <SearchIcon />
                <AlertTitle>
                  Nincs preferált tulajdonsággal rendelkező szabály.
                </AlertTitle>
              </Alert>
            )}
          </div>
        </DndContext>
        <Separator />
        <div className="grid gap-4">
          <Item className="p-0">
            <ItemContent>
              <ItemTitle>Csak kizárásra használt szabályok</ItemTitle>
              <ItemDescription>
                Itt olyan beállítások vannak, ahol nincs preferált érték - csak
                azt mondod meg, mit ne mutasson. Emiatt nem részei a preferencia
                sorrendnek.
              </ItemDescription>
            </ItemContent>
          </Item>
          <div className="grid gap-3">
            {blockedPreferences.map((preference) => (
              <Fragment key={preference.preference}>
                {renderPreference(preference)}
              </Fragment>
            ))}
            {blockedPreferences.length === 0 && (
              <Alert>
                <SearchIcon />
                <AlertTitle>Nincs kitiltásra használt szabály.</AlertTitle>
              </Alert>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
