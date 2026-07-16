import { useForm } from '@tanstack/react-form'
import { useSuspenseQuery } from '@tanstack/react-query'
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
import { Label } from '@/shared/components/ui/label'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  useSystemIndexersCleanup,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'

const schema = z.object({
  hitAndRun: z.boolean(),
  keepSeed: z.coerce
    .number<string>(t`Must be a number`)
    .positive(t`Must be a positive number.`)
    .nullable(),
})

export function KeepSeeding() {
  const { data: systemSetting } = useSuspenseQuery(getSystemSettings)

  const confirmDialog = useConfirmDialog()

  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()
  const { mutateAsync: cleanupIndexers } = useSystemIndexersCleanup()

  const keepSeedDays = useMemo(() => {
    if (systemSetting.keepSeedSeconds > 0) {
      const days = systemSetting.keepSeedSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [systemSetting.keepSeedSeconds])

  const form = useForm({
    defaultValues: {
      hitAndRun: systemSetting.hitAndRun,
      keepSeed: keepSeedDays,
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
        let keepSeedSeconds = 0

        if (value.keepSeed) {
          const days = Number(value.keepSeed)
          keepSeedSeconds = days * 24 * 60 * 60
        }

        await updateSetting({
          keepSeedSeconds,
          hitAndRun: value.hitAndRun,
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleCleanup: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()

    await confirmDialog.confirm({
      title: t`Are you sure you want to run a manual check?`,
      description: t`Even if you run this, the scheduled check at dawn will still run.`,
      onConfirm: async () => {
        try {
          await cleanupIndexers()
          toast.success(t`Manual check ran successfully.`)
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
        <CardTitle><Trans>Automatic torrent deletion</Trans></CardTitle>
        <CardDescription>
          <Trans>The check runs every day at dawn, but a torrent is only deleted if all the set conditions are met.</Trans>
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form.Field name="hitAndRun">
          {(field) => (
            <div className="grid gap-1">
              <Label htmlFor={field.name} className="flex items-start gap-3">
                <p className="flex-1 text-sm leading-none font-medium">
                  <Trans>Hit'n'Run based deletion</Trans>
                </p>
                <Switch
                  id={field.name}
                  checked={field.state.value}
                  onCheckedChange={field.handleChange}
                />
              </Label>
              <p className="text-muted-foreground text-sm">
                <Trans>Checks completion based on the tracker, and can only be deleted after that.</Trans>
              </p>
            </div>
          )}
        </form.Field>
        <div className="grid gap-3">
          <form.Field name="keepSeed">
            {(field) => (
              <div className="grid gap-3">
                <div className="grid gap-1">
                  <Label
                    htmlFor={field.name}
                    className="flex items-start gap-3"
                  >
                    <p className="flex-1 text-sm leading-none font-medium">
                      <Trans>Playback based deletion</Trans>
                    </p>
                    <Switch
                      id={field.name}
                      checked={field.state.value !== null}
                      onCheckedChange={(checked) => {
                        field.setValue(checked ? '4' : null)
                      }}
                    />
                  </Label>
                  <p className="text-muted-foreground text-sm">
                    <Trans>The torrent can only be deleted if the set time has passed since the last playback.</Trans>
                  </p>
                </div>
                {field.state.value !== null && (
                  <Field>
                    <InputGroup>
                      <InputGroupInput
                        placeholder={t`After how many days?`}
                        inputMode="numeric"
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => {
                          field.handleChange(e.target.value)
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
              </div>
            )}
          </form.Field>
        </div>
        <Separator />
        <Item variant="default" className="p-0">
          <ItemContent>
            <ItemTitle><Trans>Check torrents</Trans></ItemTitle>
            <ItemDescription>
              <Trans>Start checking torrents!</Trans>
            </ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="destructive"
              className="rounded-full"
              onClick={handleCleanup}
            >
              <BrushCleaningIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
