import type { DragEndEvent } from '@dnd-kit/core'
import { DndContext } from '@dnd-kit/core'
import {
  restrictToVerticalAxis,
  restrictToWindowEdges,
} from '@dnd-kit/modifiers'
import { SortableContext } from '@dnd-kit/sortable'
import { useQuery } from '@tanstack/react-query'

import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import type { ResolutionEnum } from '@/shared/lib/source-client'
import { cn } from '@/shared/lib/utils'
import { getMetadata } from '@/shared/queries/metadata'

import { SelectorItem } from '../selector-item'
import { SortableSelectorItem } from '../sortable-selector-item'
import { Separator } from '../ui/separator'

type ResolutionSelectorProps = {
  items: Array<ResolutionEnum>
  onAdd: (item: ResolutionEnum) => void
  onDelete: (item: ResolutionEnum) => void
  onSortableDragEnd: (event: DragEndEvent) => void
} & React.ComponentProps<'div'>

export function ResolutionsSelector(props: ResolutionSelectorProps) {
  const { items, onAdd, onDelete, onSortableDragEnd, className, ...rest } =
    props

  const { data: metadata } = useQuery(getMetadata)
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { getResolutionLabel } = useMetadataLabel()

  const inactiveResolutions = metadata.resolutions.filter(
    (resolution) => !items.includes(resolution.value),
  )
  const hasInactiveResolution = inactiveResolutions.length > 0

  return (
    <div className={cn('grid gap-3', className)} {...rest}>
      <DndContext
        onDragEnd={onSortableDragEnd}
        modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
      >
        <SortableContext items={items}>
          {items.map((item) => (
            <SortableSelectorItem
              key={item}
              item={item}
              label={getResolutionLabel(item)}
              isDisabled={item.length === 1}
              onDelete={onDelete}
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
              onAdd={onAdd}
            />
          ))}
        </>
      )}
    </div>
  )
}
