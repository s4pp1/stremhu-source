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
import type { AudioQualityEnum } from '@/shared/lib/source-client'
import { assertExists, cn } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'

import { SelectorItem } from '../selector-item'
import { SortableSelectorItem } from '../sortable-selector-item'
import { Separator } from '../ui/separator'

type AudioCodecsSelector = {
  items: Array<AudioQualityEnum>
  onChangeItems: (items: Array<AudioQualityEnum>) => void
} & React.ComponentProps<'div'>

export function AudioCodecsSelector(props: AudioCodecsSelector) {
  const { items, onChangeItems, className, ...rest } = props

  const { data: metadata } = useQuery(getMetadata)
  assertExists(metadata)

  const { getAudioCodecLabel } = useMetadata()

  const inactiveVideoQualities = metadata.audioCodecs.filter(
    (audioCodec) => !items.includes(audioCodec.value),
  )
  const hasInactiveVideoQualities = inactiveVideoQualities.length > 0

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
    const oldIndex = localItems.indexOf(active.id as AudioQualityEnum)
    const newIndex = localItems.indexOf(over.id as AudioQualityEnum)
    if (oldIndex < 0 || newIndex < 0) return

    const nextItems = [...localItems]
    const [movedItem] = nextItems.splice(oldIndex, 1)
    nextItems.splice(newIndex, 0, movedItem)

    setLocalItems(nextItems)
  }

  const handleAdd = (item: AudioQualityEnum) => {
    const nextItems = [...localItems, item]
    setLocalItems(nextItems)
  }

  const handleDelete = (item: AudioQualityEnum) => {
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
              label={getAudioCodecLabel(item)}
              isDisabled={localItems.length === 1}
              onDelete={handleDelete}
            />
          ))}
        </SortableContext>
      </DndContext>
      {hasInactiveVideoQualities && (
        <>
          <Separator />
          {inactiveVideoQualities.map((videoQuality) => (
            <SelectorItem
              key={videoQuality.value}
              label={videoQuality.label}
              value={videoQuality.value}
              onAdd={handleAdd}
            />
          ))}
        </>
      )}
    </div>
  )
}
