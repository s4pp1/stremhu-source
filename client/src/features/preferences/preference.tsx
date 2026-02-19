import type { LinkProps } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import { upperFirst } from 'lodash'
import { EditIcon, TrashIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemTitle,
} from '@/shared/components/ui/item'
import { useMetadata } from '@/shared/hooks/use-metadata'
import { parseApiError } from '@/shared/lib/utils'
import type { PreferenceDto } from '@/shared/type/preference.dto'

import { BadgesSection } from './badges-section'

interface PreferenceProps {
  preference: PreferenceDto
  toEditLink: LinkProps
  onDelete: (preference: PreferenceDto) => Promise<void>
}

export function Preference(props: PreferenceProps) {
  const { preference, toEditLink, onDelete } = props

  const { getPreference, getPreferenceItem } = useMetadata()

  const confirmDialog = useConfirmDialog()

  const preferenceName = getPreference(preference.preference).label

  const handleDelete: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.stopPropagation()

    await confirmDialog.confirm({
      title: `Biztosan törlöd?`,
      description: (
        <>
          A(z){' '}
          <span className="font-bold break-all capitalize">
            {preferenceName}
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
            {upperFirst(preferenceName)} konfigurációja
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
      <div className="grid gap-3">
        {preference.preferred.length !== 0 && (
          <BadgesSection
            title="Preferált tulajdonságok"
            items={preference.preferred.map((item) => {
              const preferenceItem = getPreferenceItem(
                preference.preference,
                item,
              )
              return {
                label: preferenceItem.label,
                value: preferenceItem.value,
              }
            })}
          />
        )}
        {preference.blocked.length !== 0 && (
          <BadgesSection
            title="Kizárt tulajdonságok"
            items={preference.blocked.map((item) => {
              const preferenceItem = getPreferenceItem(
                preference.preference,
                item,
              )
              return {
                label: preferenceItem.label,
                value: preferenceItem.value,
                variant: 'destructive',
              }
            })}
          />
        )}
      </div>
    </div>
  )
}
