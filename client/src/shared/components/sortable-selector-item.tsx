import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { MoveVerticalIcon, TrashIcon } from 'lucide-react'

import type { LanguageEnum, ResolutionEnum } from '@/shared/lib/source-client'

import { Button } from './ui/button'
import { Label } from './ui/label'

interface SortableSelectorItemProps<T> {
  item: T
  label: string
  isDisabled: boolean
  onDelete: (item: T) => void
}

export function SortableSelectorItem<T extends ResolutionEnum | LanguageEnum>(
  props: SortableSelectorItemProps<T>,
) {
  const { item, label, isDisabled, onDelete } = props

  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: item })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div ref={setNodeRef} style={style} className="flex justify-between">
      <div className="flex items-center space-x-4">
        <Button
          size="icon"
          className="rounded-full size-6"
          {...attributes}
          {...listeners}
        >
          <MoveVerticalIcon />
        </Button>
        <Label>{label}</Label>
      </div>
      <Button
        variant="destructive"
        size="icon"
        className="rounded-full size-6"
        disabled={isDisabled}
        onClick={() => onDelete(item)}
      >
        <TrashIcon />
      </Button>
    </div>
  )
}
