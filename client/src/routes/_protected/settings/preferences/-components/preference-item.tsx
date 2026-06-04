import type { ReactNode } from 'react'

import {
  Item,
  ItemActions,
  ItemHeader,
  ItemTitle,
} from '@/shared/components/ui/item'
import type { AttributeResponse } from '@/shared/lib/source/source-client'

export interface PreferenceItemProps {
  attribute: AttributeResponse
  actions?: ReactNode[]
}

export function PreferenceItem(props: PreferenceItemProps) {
  const { attribute, actions } = props

  return (
    <Item variant="muted">
      <ItemHeader>
        <ItemTitle>{attribute.name}</ItemTitle>
        {actions !== undefined && <ItemActions>{actions}</ItemActions>}
      </ItemHeader>
    </Item>
  )
}
