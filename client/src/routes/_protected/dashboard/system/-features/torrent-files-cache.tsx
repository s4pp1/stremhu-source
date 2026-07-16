import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
import { BrushCleaningIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'
import { t } from '@lingui/core/macro'
import { Trans } from '@lingui/react/macro'

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
import { Separator } from '@/shared/components/ui/separator'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  useSystemSettingsUpdate,
  useSystemTorrentFilesCleanup,
} from '@/shared/queries/system'

const schema = z.object({
  cacheRetention: z.coerce
    .number<string>(t`Must be a number`)
    .positive(t`Must be a positive number.`)
    .nullable(),
})

export function TorrentFilesCache() {
  const { data: systemSettings } = useSuspenseQuery(getSystemSettings)

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()
  const { mutateAsync: cleanupSystemTorrentFiles } =
    useSystemTorrentFilesCleanup()

  const cacheRetentionDays = useMemo(() => {
    if (systemSettings.cacheRetentionSeconds > 0) {
      const days = systemSettings.cacheRetentionSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [systemSettings.cacheRetentionSeconds])

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
        let cacheRetentionSeconds = 0

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
      title: t`Are you sure you want to clear the cache?`,
      description: t`Files belonging to active torrents will not be deleted.`,
      onConfirm: async () => {
        try {
          await cleanupSystemTorrentFiles()
          toast.success(t`Cache cleanup ran successfully.`)
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
        <CardTitle><Trans>Manage torrent files cache</Trans></CardTitle>
        <CardDescription>
          <Trans>Specify how long after unused torrent files should be deleted</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="cacheRetention">
          {(field) => (
            <Field>
              <InputGroup>
                <InputGroupInput
                  placeholder={t`No cache cleanup`}
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
                  <InputGroupText><Trans>days</Trans></InputGroupText>
                </InputGroupAddon>
              </InputGroup>
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
        <Separator />
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle><Trans>Clear cache</Trans></ItemTitle>
            <ItemDescription>
              <Trans>All unused cache will be deleted!</Trans>
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
