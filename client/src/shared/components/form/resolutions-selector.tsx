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
import type { ResolutionEnum } from '@/shared/lib/source-client'
import { assertExists, cn } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'

import { SelectorItem } from '../selector-item'
import { SortableSelectorItem } from '../sortable-selector-item'
import { Separator } from '../ui/separator'

type ResolutionsSelector = {
  items: Array<ResolutionEnum>
  onChangeItems: (items: Array<ResolutionEnum>) => void
} & React.ComponentProps<'div'>

export function ResolutionsSelector(props: ResolutionsSelector) {
  const { items, onChangeItems, className, ...rest } = props

  const { data: metadata } = useQuery(getMetadata)
  assertExists(metadata)

  const { getResolutionLabel } = useMetadata()

  const inactiveResolutions = metadata.resolutions.filter(
    (resolution) => !items.includes(resolution.value),
  )
  const hasInactiveResolution = inactiveResolutions.length > 0

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
      console.log('useEffect')
      onChangeItems(localItems)
    }
  }, [localItems])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (!over || active.id === over.id) return
    const oldIndex = localItems.indexOf(active.id as ResolutionEnum)
    const newIndex = localItems.indexOf(over.id as ResolutionEnum)
    if (oldIndex < 0 || newIndex < 0) return

    const nextItems = [...localItems]
    const [movedItem] = nextItems.splice(oldIndex, 1)
    nextItems.splice(newIndex, 0, movedItem)

    setLocalItems(nextItems)
  }

  const handleAdd = (item: ResolutionEnum) => {
    const nextItems = [...localItems, item]
    setLocalItems(nextItems)
  }

  const handleDelete = (item: ResolutionEnum) => {
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
              label={getResolutionLabel(item)}
              isDisabled={localItems.length === 1}
              onDelete={handleDelete}
            />
          ))}
        </SortableContext>
      </DndContext>
      {hasInactiveResolution && (
        <>
          <Separator />
          {inactiveResolutions.map((inactiveResolution) => (
            <SelectorItem
              key={inactiveResolution.value}
              label={inactiveResolution.label}
              value={inactiveResolution.value}
              onAdd={handleAdd}
            />
          ))}
        </>
      )}
    </div>
  )
}
