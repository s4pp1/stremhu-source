import type { LinkProps } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import { upperFirst } from 'lodash'
import { EditIcon, TrashIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import type { PreferenceResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'

interface PreferenceProps {
  preference: PreferenceResponse
  toEditLink: LinkProps
  onDelete: (preference: PreferenceResponse) => Promise<void>
}

export function Preference(props: PreferenceProps) {
  const { preference, toEditLink, onDelete } = props

  const confirmDialog = useConfirmDialog()

  const handleDelete: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd?`,
      description: (
        <>
          A(z){' '}
          <span className="font-bold break-all capitalize">
            {preference.name}
          </span>{' '}
          törlésével az adatok is törlésre kerülnek.
        </>
      ),
      confirmText: 'Törlés',
      onConfirm: async () => {
        try {
          await onDelete(preference)
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  return (
    <div className="grid gap-2 border border-transparent rounded-md bg-muted/50 p-4">
      <Item className="p-0">
        <ItemContent>
          <ItemTitle className="line-clamp-2 break-all">
            {upperFirst(preference.name)} konfigurációja
          </ItemTitle>
        </ItemContent>
        <ItemActions>
          <Button asChild size="icon-sm" className="rounded-full">
            <Link onPointerDown={(e) => e.stopPropagation()} {...toEditLink}>
              <EditIcon />
            </Link>
          </Button>
          <Button
            size="icon-sm"
            className="rounded-full"
            variant="destructive"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={handleDelete}
          >
            <TrashIcon />
          </Button>
        </ItemActions>
      </Item>
      <div className=" flex flex-wrap gap-2">
        {preference.attributes.map((attribute) => (
          <Badge key={attribute.id} variant="default">
            {attribute.name}
          </Badge>
        ))}
      </div>
    </div>
  )
}
