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
import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { sortBy } from 'lodash'
import { GrabIcon, PlusIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { SortableWrapper } from '@/shared/components/sortable-wrapper'
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
import { assertExists } from '@/shared/lib/utils'
import {
  getMePreferences,
  useReorderMePreference,
} from '@/shared/queries/me-preferences'

import { Preference } from './-components/preference'
import { OtherPreferences } from './-features/other-preferences'
import { SETTINGS_PREFERENCES_NAME } from './route'

export const Route = createFileRoute('/_protected/settings/preferences/')({
  component: RouteComponent,
})

function RouteComponent() {
  const { data: mePreferences } = useQuery(getMePreferences)
  assertExists(mePreferences)

  const { mutateAsync: reorderMePreference } = useReorderMePreference()

  const preferredPreferences = useMemo(
    () =>
      sortBy(
        mePreferences.filter((preference) => preference.preferred.length > 0),
        'order',
      ),
    [mePreferences],
  )
  const blockedPreferences = useMemo(
    () =>
      mePreferences.filter(
        (preference) =>
          preference.blocked.length !== 0 && preference.preferred.length === 0,
      ),
    [mePreferences],
  )

  const [items, setItems] = useState(preferredPreferences)

  useEffect(() => {
    setItems(preferredPreferences)
  }, [preferredPreferences])

  const onReorderItems = async (event: DragEndEvent) => {
    const { over, active } = event
    if (!over || active.id === over.id) return

    const oldIndex = items.findIndex((item) => item.preference === active.id)
    const newIndex = items.findIndex((item) => item.preference === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(items, oldIndex, newIndex)
    setItems(reordered)

    await reorderMePreference({
      preferences: reordered.map((item) => item.preference),
    })
  }

  return (
    <div className="grid gap-8">
      <Card>
        <CardHeader>
          <CardTitle>{SETTINGS_PREFERENCES_NAME}</CardTitle>
          <CardDescription>
            Testreszabhatod, milyen torrentek kerüljenek előre a listában, és
            mit szeretnél kizárni. A preferált tulajdonságok a sorrendet
            javítják, a kizárások pedig kiszűrik a nem kívánt találatokat.
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
          <DndContext
            onDragEnd={onReorderItems}
            modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
          >
            <div className="grid gap-4">
              <Item className="p-0">
                <ItemContent>
                  <ItemTitle>Preferencia sorrend</ItemTitle>
                  <ItemDescription>
                    Preferált tulajdonsággal rendelkező szabályok esetén
                    módosítható azok súlyozása a sorrend módosításával.
                  </ItemDescription>
                </ItemContent>
                <ItemActions>
                  <ItemMedia variant="icon" className="rounded-full">
                    <GrabIcon />
                  </ItemMedia>
                </ItemActions>
              </Item>
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
                    <Preference
                      key={preference.preference}
                      preference={preference}
                    />
                  </SortableWrapper>
                ))}
              </SortableContext>
            </div>
          </DndContext>
          <Separator />
          <div className="grid gap-4">
            <Item className="p-0">
              <ItemContent>
                <ItemTitle>Csak kizárásra használt szabályok</ItemTitle>
                <ItemDescription>
                  Itt olyan beállítások vannak, ahol nincs preferált érték -
                  csak azt mondod meg, mit ne mutasson. Emiatt nem részei a
                  preferencia sorrendnek.
                </ItemDescription>
              </ItemContent>
            </Item>
            {blockedPreferences.map((preference) => (
              <Preference key={preference.preference} preference={preference} />
            ))}
          </div>
        </CardContent>
      </Card>
      <Separator />
      <OtherPreferences />
    </div>
  )
}
