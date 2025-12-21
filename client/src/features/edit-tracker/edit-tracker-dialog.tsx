import { isEmpty } from 'lodash'
import { useMemo } from 'react'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { useAppForm } from '@/shared/contexts/form-context'
import { useMetadata } from '@/shared/hooks/use-metadata'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateTracker } from '@/shared/queries/trackers'

import { HIT_AND_RUN_OPTIONS } from './edit-tracker.contant'
import { EditTrackerOptionEnum } from './edit-tracker.type'
import type { EditTrackerDialog } from './edit-tracker.type'

const schema = z.object({
  hitAndRunEnum: z.enum(EditTrackerOptionEnum),
  keepSeed: z.coerce
    .number<string>('Csak szám adható meg')
    .positive('Csak pozitív szám adható meg.')
    .nullable(),
  downloadFullTorrent: z.boolean(),
})

export function EditTrackerDialog(dialog: OpenedDialog & EditTrackerDialog) {
  const { tracker } = dialog.options

  const { getTrackerLabel, getTrackerFullDownload } = useMetadata()

  const dialogsStore = useDialogsStore()

  const { mutateAsync: updateTracker } = useUpdateTracker(tracker.tracker)

  const hitAndRunEnum = useMemo(() => {
    if (tracker.hitAndRun === true) {
      return EditTrackerOptionEnum.ENABLED
    }

    if (tracker.hitAndRun === false) {
      return EditTrackerOptionEnum.DISABLED
    }

    return EditTrackerOptionEnum.INHERIT
  }, [tracker.hitAndRun])

  const keepSeed = useMemo(() => {
    if (tracker.keepSeedSeconds) {
      const days = tracker.keepSeedSeconds / (24 * 60 * 60)
      return `${days}`
    }

    return null
  }, [tracker.keepSeedSeconds])

  const form = useAppForm({
    defaultValues: {
      hitAndRunEnum,
      keepSeed,
      downloadFullTorrent: tracker.downloadFullTorrent,
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        let hitAndRun = null

        if (value.hitAndRunEnum === EditTrackerOptionEnum.ENABLED) {
          hitAndRun = true
        }

        if (value.hitAndRunEnum === EditTrackerOptionEnum.DISABLED) {
          hitAndRun = false
        }

        if (value.hitAndRunEnum === EditTrackerOptionEnum.INHERIT) {
          hitAndRun = null
        }

        let keepSeedSeconds = null
        if (value.keepSeed) {
          const days = Number(value.keepSeed)
          keepSeedSeconds = days * 24 * 60 * 60
        }

        await updateTracker({
          ...value,
          hitAndRun,
          keepSeedSeconds,
        })

        dialogsStore.closeDialog(dialog.id)
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.closeDialog(dialog.id)
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-md"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <form name="add-user" className="grid gap-4" onSubmit={onSubmit}>
            <DialogHeader>
              <DialogTitle>
                "{getTrackerLabel(tracker.tracker)}" módosítása
              </DialogTitle>
              <DialogDescription>
                Állítsd be a tracker-re vonatkozó beállításokat és írd felül a
                globális beállítások ennél a tracker-nél.
              </DialogDescription>
            </DialogHeader>

            <form.Field name="downloadFullTorrent">
              {(field) => (
                <div className="flex items-center space-x-2">
                  <Switch
                    id={field.name}
                    checked={field.state.value}
                    disabled={getTrackerFullDownload(tracker.tracker)}
                    onCheckedChange={field.handleChange}
                  />
                  <Label htmlFor="airplane-mode">
                    Teljes torrent letöltése
                  </Label>
                </div>
              )}
            </form.Field>

            <Separator />

            <form.Field name="hitAndRunEnum">
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={field.name}>
                    Hit'n'Run felülbírálása
                  </FieldLabel>
                  <Select
                    value={field.state.value}
                    name={field.name}
                    onValueChange={(value: EditTrackerOptionEnum) =>
                      field.handleChange(value)
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {HIT_AND_RUN_OPTIONS.map((han) => (
                        <SelectItem key={han.value} value={han.value}>
                          {han.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
            <form.Field name="keepSeed">
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={field.name}>
                    Lejátszás alapú seedben tartás felülbírálása
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      placeholder="Globális beállítás használata"
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

            <DialogFooter>
              <form.SubscribeButton variant="outline" onClick={handleClose}>
                Mégsem
              </form.SubscribeButton>
              <form.SubscribeButton type="submit">
                Módosítás
              </form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
