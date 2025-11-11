import { Item, ItemContent, ItemMedia, ItemTitle } from './ui/item'
import { Spinner } from './ui/spinner'

interface DefaultLoadingProps {
  message?: string
}

export function DefaultLoading(props: DefaultLoadingProps) {
  const { message = 'Komponensek betöltése' } = props

  return (
    <div className="flex justify-center py-4">
      <Item variant="muted" className="rounded-4xl">
        <ItemMedia>
          <Spinner />
        </ItemMedia>
        <ItemContent>
          <ItemTitle className="line-clamp-1 pr-2">{message}</ItemTitle>
        </ItemContent>
      </Item>
    </div>
  )
}
