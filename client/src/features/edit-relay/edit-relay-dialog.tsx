import { isEmpty } from 'lodash'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { useMemo } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
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
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import { useUpdateRelaySetting } from '@/shared/queries/relay'

import type { EditRelayDialog } from './edit-relay.type'

const schema = z.object({
  port: z.coerce.number<string>().min(1),
  enableUpnpAndNatpmp: z.boolean(),
  downloadLimit: z.coerce.number<string>().positive().nullable(),
  uploadLimit: z.coerce.number<string>().positive().nullable(),
  connectionsLimit: z.coerce.number<string>().min(1),
  torrentConnectionsLimit: z.coerce.number<string>().min(1),
})

export function EditRelayDialog(dialog: OpenedDialog & EditRelayDialog) {
  const { relay } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: updateRelaySetting } = useUpdateRelaySetting()

  const setting = useMemo(() => {
    let downloadLimit = null
    if (relay.downloadLimit !== 0) {
      downloadLimit = `${relay.downloadLimit / 125_000}`
    }

    let uploadLimit = null
    if (relay.uploadLimit !== 0) {
      uploadLimit = `${relay.uploadLimit / 125_000}`
    }

    return {
      ...relay,
      downloadLimit,
      uploadLimit,
      connectionsLimit: relay.connectionsLimit.toString(),
      torrentConnectionsLimit: relay.torrentConnectionsLimit.toString(),
    }
  }, [relay])

  const form = useAppForm({
    defaultValues: {
      port: setting.port.toString(),
      enableUpnpAndNatpmp: setting.enableUpnpAndNatpmp,
      downloadLimit: setting.downloadLimit,
      uploadLimit: setting.uploadLimit,
      connectionsLimit: setting.connectionsLimit,
      torrentConnectionsLimit: setting.torrentConnectionsLimit,
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        // Letöltési sebesség
        let downloadLimit = 0

        if (value.downloadLimit !== null) {
          downloadLimit = Number(value.downloadLimit) * 125_000
        }

        // Feltöltési sebesség
        let uploadLimit = 0

        if (value.uploadLimit !== null) {
          uploadLimit = Number(value.uploadLimit) * 125_000
        }

        await updateRelaySetting({
          ...value,
          port: Number(value.port),
          connectionsLimit: Number(value.connectionsLimit),
          torrentConnectionsLimit: Number(value.torrentConnectionsLimit),
          downloadLimit,
          uploadLimit,
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
              <DialogTitle>Relay konfigurálása</DialogTitle>
              <DialogDescription>
                Állítsd be a StremHU Relay-re vonatkozó konfigurációkat.
              </DialogDescription>
            </DialogHeader>

            <form.Field name="port">
              {(field) => (
                <Field>
                  <FieldLabel>Port a bejövő kapcsolatokhoz</FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      disabled
                      placeholder="Nincs limitálva"
                      inputMode="numeric"
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => {
                        const value = e.target.value

                        if (isEmpty(value)) {
                          field.handleChange('0')
                        } else {
                          field.handleChange(e.target.value)
                        }
                      }}
                    />
                  </InputGroup>
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>
            <form.Field name="enableUpnpAndNatpmp">
              {(field) => (
                <div className="flex items-center space-x-2">
                  <Switch
                    id={field.name}
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                  <Label htmlFor="airplane-mode">
                    UPnP / NAT-PMP használata a routeren a porttovábbításhoz
                  </Label>
                </div>
              )}
            </form.Field>

            <Separator />

            <form.Field name="downloadLimit">
              {(field) => (
                <Field>
                  <FieldLabel>Letöltés</FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      placeholder="Nincs limitálva"
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
                      <InputGroupText>Mbit/s</InputGroupText>
                    </InputGroupAddon>
                  </InputGroup>
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>
            <form.Field name="uploadLimit">
              {(field) => (
                <Field>
                  <FieldLabel>Feltöltés</FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      placeholder="Nincs limitálva"
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
                      <InputGroupText>Mbit/s</InputGroupText>
                    </InputGroupAddon>
                  </InputGroup>
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>

            <Separator />

            <form.Field name="connectionsLimit">
              {(field) => (
                <Field>
                  <FieldLabel>Globális kapcsolatok maximális száma</FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      inputMode="numeric"
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => {
                        field.handleChange(e.target.value)
                      }}
                    />
                  </InputGroup>
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>
            <form.Field name="torrentConnectionsLimit">
              {(field) => (
                <Field>
                  <FieldLabel>
                    Torrentenkénti kapcsolatok maximális száma
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      inputMode="numeric"
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => {
                        field.handleChange(e.target.value)
                      }}
                    />
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
              <form.SubscribeButton type="submit">Mentés</form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
