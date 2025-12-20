import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
import { BrushCleaningIcon } from 'lucide-react'
import { useMemo } from 'react'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'
import { useCleanupTorrentsCache } from '@/shared/queries/torrents-cache'

const schema = z.object({
  cacheRetention: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.')
    .nullable(),
})

export function TorrentFilesCache() {
  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateSetting } = useUpdateSetting()
  const { mutateAsync: cleanupTorrentsCache } = useCleanupTorrentsCache()

  const cacheRetentionDays = useMemo(() => {
    if (setting.cacheRetentionSeconds) {
      const days = setting.cacheRetentionSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [setting.cacheRetentionSeconds])

  const form = useForm({
    defaultValues: {
      cacheRetention: cacheRetentionDays,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        let cacheRetentionSeconds = null

        if (value.cacheRetention) {
          const days = Number(value.cacheRetention)
          cacheRetentionSeconds = days * 24 * 60 * 60
        }

        await updateSetting({
          cacheRetentionSeconds,
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleTorrentsCacheCleanup: MouseEventHandler<
    HTMLButtonElement
  > = async (e) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: 'Biztos ki szeretnéd üríteni a cache-t?',
      description: 'Az aktív torrentekhez tartozó fájlok nem lesznek törölve.',
      onConfirm: async () => {
        try {
          await cleanupTorrentsCache()
          toast.success('A cache törlés sikeresen lefutott.')
        } catch (error) {
          const message = parseApiError(error)
          toast.error(message)
          throw error
        }
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Torrent fájlok cache kezelése</CardTitle>
        <CardDescription>
          Add meg, mennyi idő után törlődjenek a nem használt torrent fájlok
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <form.Field name="cacheRetention">
          {(field) => (
            <Field>
              <InputGroup>
                <InputGroupInput
                  placeholder="Nincs cache törlés"
                  inputMode="numeric"
                  id={field.name}
                  name={field.name}
                  value={field.state.value ?? ''}
                  onBlur={field.handleBlur}
                  onChange={(e) => {
                    const value = e.target.value

                    if (isEmpty(value)) {
                      field.handleChange(null)
                    } else {
                      field.handleChange(e.target.value)
                    }
                  }}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupText>nap</InputGroupText>
                </InputGroupAddon>
              </InputGroup>
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle>Cache ürítése</ItemTitle>
            <ItemDescription>
              Minden használaton kívüli cache törlésre kerül!
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="destructive"
              className="rounded-full"
              onClick={handleTorrentsCacheCleanup}
            >
              <BrushCleaningIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
