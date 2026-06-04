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
import { useSuspenseQuery } from '@tanstack/react-query'
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
import type { PreferenceResponse } from '@/shared/lib/source/source-client'
import { getPreferences } from '@/shared/queries/preferences'

type PreferencesSectionProps = {
  preferences: PreferenceResponse[]
  toCreateLink: LinkProps
  renderPreference: (preference: PreferenceResponse) => ReactNode
  onReorder: (preferenceIds: string[]) => Promise<void>
}

export function PreferencesSection(props: PreferencesSectionProps) {
  const { data: allPreferences } = useSuspenseQuery(getPreferences)

  const { preferences, toCreateLink, renderPreference, onReorder } = props

  const disableCreatePreference = useMemo(() => {
    return allPreferences.length === preferences.length
  }, [allPreferences.length, preferences.length])

  const preferredPreferences = useMemo(
    () =>
      sortBy(
        preferences.filter((preference) => preference.attributes.length > 0),
        'order',
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

    const oldIndex = items.findIndex((item) => item.id === active.id)
    const newIndex = items.findIndex((item) => item.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(items, oldIndex, newIndex)
    setItems(reordered)

    await onReorder(reordered.map((item) => item.id))
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
        {!disableCreatePreference && (
          <CardAction>
            <Button asChild size="icon-sm" className="rounded-full">
              <Link {...toCreateLink}>
                <PlusIcon />
              </Link>
            </Button>
          </CardAction>
        )}
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
              items={items.map((preferredPreference) => preferredPreference.id)}
              strategy={verticalListSortingStrategy}
            >
              {items.map((preference) => (
                <SortableWrapper
                  key={preference.id}
                  item={preference}
                  resolveId={(i) => i.id}
                >
                  <Fragment key={preference.id}>
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
        </div>
      </CardContent>
    </Card>
  )
}
