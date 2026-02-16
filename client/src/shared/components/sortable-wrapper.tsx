import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { PropsWithChildren } from 'react'

type SortableWrapperProps<T> = {
  item: T
  resolveId: (item: T) => string
}

export function SortableWrapper<T>(
  props: PropsWithChildren<SortableWrapperProps<T>>,
) {
  const { item, resolveId, children } = props

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
    rect,
  } = useSortable({ id: resolveId(item) })

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    ...(isDragging &&
      rect.current && {
        width: rect.current.width,
        height: rect.current.height,
      }),
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="cursor-grab"
    >
      {children}
    </div>
  )
}
