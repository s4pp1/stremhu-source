import { PlusIcon } from 'lucide-react'

import { Button } from './ui/button'
import { Label } from './ui/label'

interface SelectorItemProps<T> {
  value: T
  label: string
  onAdd: (item: T) => void
}

export function SelectorItem<T>(props: SelectorItemProps<T>) {
  const { value, label, onAdd } = props

  return (
    <div className="flex justify-between">
      <Label>{label}</Label>
      <Button
        size="icon"
        className="rounded-full size-6"
        onClick={() => onAdd(value)}
      >
        <PlusIcon />
      </Button>
    </div>
  )
}
