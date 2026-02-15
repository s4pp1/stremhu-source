import type { ReactNode } from 'react'

import {
  Item,
  ItemActions,
  ItemHeader,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type {
  AudioQualityEnum,
  LanguageEnum,
  PreferenceEnum,
  ResolutionEnum,
  SourceEnum,
  TrackerEnum,
  VideoQualityEnum,
} from '@/shared/lib/source-client'

export interface PreferenceItemProps {
  preference: PreferenceEnum
  preferenceItem:
    | TrackerEnum
    | LanguageEnum
    | ResolutionEnum
    | VideoQualityEnum
    | SourceEnum
    | AudioQualityEnum
  actions?: Array<ReactNode>
}

export function PreferenceItem(props: PreferenceItemProps) {
  const { preference, preferenceItem, actions } = props

  const { getPreferenceItem } = useMetadata()

  const item = getPreferenceItem(preference, preferenceItem)

  return (
    <Item variant="muted">
      <ItemHeader>
        <ItemTitle>{item.label}</ItemTitle>
        {actions !== undefined && <ItemActions>{actions}</ItemActions>}
      </ItemHeader>
    </Item>
  )
}
