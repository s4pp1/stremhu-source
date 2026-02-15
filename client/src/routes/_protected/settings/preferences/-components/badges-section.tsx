import { Badge } from '@/shared/components/ui/badge'

type BadgesSectionItem = {
  value: string
  label: string
  variant?: 'destructive'
}

type BadgesSectionProps = {
  title: string
  items: Array<BadgesSectionItem>
}

export function BadgesSection(props: BadgesSectionProps) {
  const { title, items } = props

  return (
    <div className="grid gap-1">
      <div className="text-muted-foreground text-xs font-medium">{title}</div>
      <div className="flex gap-2">
        {items.map((item) => (
          <Badge variant={item.variant} key={item.value}>
            {item.label}
          </Badge>
        ))}
      </div>
    </div>
  )
}
