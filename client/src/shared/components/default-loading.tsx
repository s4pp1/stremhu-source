import { Item, ItemContent, ItemMedia, ItemTitle } from './ui/item'
import { Spinner } from './ui/spinner'
import { Trans } from '@lingui/react/macro'
import type { ReactNode } from 'react'

interface DefaultLoadingProps {
  message?: ReactNode
}

export function DefaultLoading(props: DefaultLoadingProps) {
  const { message } = props

  return (
    <div className="flex justify-center py-4">
      <Item variant="muted" className="rounded-4xl">
        <ItemMedia>
          <Spinner />
        </ItemMedia>
        <ItemContent>
          <ItemTitle className="line-clamp-1 pr-2">{message || <Trans>Loading components</Trans>}</ItemTitle>
        </ItemContent>
      </Item>
    </div>
  )
}
