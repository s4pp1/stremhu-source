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
import { ItemMedia } from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import type { PreferenceResponse } from '@/shared/lib/source/source-client'

type PreferencesSectionProps = {
  preferences: PreferenceResponse[]
  currentPreferences: PreferenceResponse[]
  toCreateLink: LinkProps
  renderPreference: (preference: PreferenceResponse) => ReactNode
  onReorder: (preferenceIds: string[]) => Promise<void>
}

export function PreferencesSection(props: PreferencesSectionProps) {
  const {
    preferences,
    currentPreferences,
    toCreateLink,
    renderPreference,
    onReorder,
  } = props

  const disableCreatePreference = useMemo(() => {
    return currentPreferences.length === preferences.length
  }, [currentPreferences.length, preferences.length])

  const [items, setItems] = useState(currentPreferences)

  useEffect(() => {
    setItems(currentPreferences)
  }, [currentPreferences])

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
          Testreszabhatod, milyen torrentek kerüljenek előre a listában. A
          preferált tulajdonságok befolyásolják a sorrendet.
        </CardDescription>
        <CardAction className="flex items-center gap-2">
          <ItemMedia variant="icon" className="rounded-full">
            <GrabIcon />
          </ItemMedia>
          {!disableCreatePreference && (
            <Button asChild size="icon-sm" className="rounded-full">
              <Link {...toCreateLink}>
                <PlusIcon />
              </Link>
            </Button>
          )}
        </CardAction>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-8">
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
      </CardContent>
    </Card>
  )
}
