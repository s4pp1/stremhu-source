import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { cn } from '@/shared/lib/utils'

type NetworkCardProps = {
  name: string
  description: string
  isSelected?: boolean
  onSelect?: () => void
}

export function NetworkCard(props: NetworkCardProps) {
  const { name, description, isSelected = false, onSelect } = props
  return (
    <Item
      variant="outline"
      key={name}
      className={cn(
        isSelected
          ? 'bg-primary/10'
          : 'transition-all duration-200 cursor-pointer hover:bg-primary/5',
      )}
      onClick={isSelected ? undefined : onSelect}
    >
      <ItemContent>
        <ItemTitle className={cn(isSelected && 'text-primary font-semibold')}>
          {name}
        </ItemTitle>
        <ItemDescription className="line-clamp-none text-wrap">
          {description}
        </ItemDescription>
      </ItemContent>
    </Item>
  )
}
