import type { DragEndEvent } from '@dnd-kit/core'
import { DndContext } from '@dnd-kit/core'
import {
  restrictToVerticalAxis,
  restrictToWindowEdges,
} from '@dnd-kit/modifiers'
import { SortableContext } from '@dnd-kit/sortable'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { useMetadata } from '@/shared/hooks/use-metadata'
import type { LanguageEnum } from '@/shared/lib/source-client'
import { cn } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'

import { SelectorItem } from '../selector-item'
import { SortableSelectorItem } from '../sortable-selector-item'
import { Separator } from '../ui/separator'

type LanguagesSelector = {
  items: Array<LanguageEnum>
  onChangeItems: (items: Array<LanguageEnum>) => void
} & React.ComponentProps<'div'>

export function LanguagesSelector(props: LanguagesSelector) {
  const { items, onChangeItems, className, ...rest } = props

  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { getLanguageLabel } = useMetadata()

  const inactiveItems = metadata.languages.filter(
    (resolution) => !items.includes(resolution.value),
  )
  const hasInactiveItem = inactiveItems.length > 0

  const [localItems, setLocalItems] = useState(items)

  useEffect(() => {
    const stringItems = JSON.stringify(items)
    const stringLocalItems = JSON.stringify(localItems)

    if (stringItems !== stringLocalItems) {
      setLocalItems(items)
    }
  }, [items])

  useEffect(() => {
    const stringItems = JSON.stringify(items)
    const stringLocalItems = JSON.stringify(localItems)

    if (stringItems !== stringLocalItems) {
      onChangeItems(localItems)
    }
  }, [localItems])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (!over || active.id === over.id) return
    const oldIndex = localItems.indexOf(active.id as LanguageEnum)
    const newIndex = localItems.indexOf(over.id as LanguageEnum)
    if (oldIndex < 0 || newIndex < 0) return

    const nextItems = [...localItems]
    const [movedItem] = nextItems.splice(oldIndex, 1)
    nextItems.splice(newIndex, 0, movedItem)

    setLocalItems(nextItems)
  }

  const handleAdd = (item: LanguageEnum) => {
    const nextItems = [...localItems, item]
    setLocalItems(nextItems)
  }

  const handleDelete = (item: LanguageEnum) => {
    const nextItems = localItems.filter((value) => value !== item)
    setLocalItems(nextItems)
  }

  return (
    <div className={cn('grid gap-3', className)} {...rest}>
      <DndContext
        onDragEnd={handleDragEnd}
        modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
      >
        <SortableContext items={localItems}>
          {localItems.map((item) => (
            <SortableSelectorItem
              key={item}
              item={item}
              label={getLanguageLabel(item)}
              isDisabled={localItems.length === 1}
              onDelete={handleDelete}
            />
          ))}
        </SortableContext>
      </DndContext>
      {hasInactiveItem && (
        <>
          <Separator />
          {inactiveItems.map((item) => (
            <SelectorItem
              label={item.label}
              value={item.value}
              onAdd={handleAdd}
            />
          ))}
        </>
      )}
    </div>
  )
}
