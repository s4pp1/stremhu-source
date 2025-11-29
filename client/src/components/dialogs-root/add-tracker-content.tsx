import { useQuery } from '@tanstack/react-query'
import type { FormEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { TrackerEnum } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAppForm } from '@/contexts/form-context'
import { useMetadataLabel } from '@/hooks/use-metadata-label'
import { getMetadata } from '@/queries/metadata'
import { useLoginTracker } from '@/queries/trackers'
import { useDialogsStore } from '@/store/dialogs-store'

interface AddTrackerContentProps {
  activeTrackers: Array<TrackerEnum>
}

const schema = z.object({
  tracker: z.enum(TrackerEnum),
  trackerUsn: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  trackerPwd: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

export function AddTrackerContent(props: AddTrackerContentProps) {
  const { activeTrackers } = props

  const dialogsStore = useDialogsStore()

  const { data: metadata } = useQuery(getMetadata)
  const { getTrackerLabel } = useMetadataLabel()
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)

  const { mutateAsync: loginTracker } = useLoginTracker()

  const { trackers } = metadata

  const inactiveTrackers = trackers.filter(
    (tracker) => !activeTrackers.includes(tracker.value),
  )

  const form = useAppForm({
    defaultValues: {
      tracker: inactiveTrackers[0].value,
      trackerUsn: '',
      trackerPwd: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await loginTracker({
          tracker: value.tracker,
          username: value.trackerUsn,
          password: value.trackerPwd,
        })
        toast.success(
          `Sikeres csatlakozás az ${getTrackerLabel(value.tracker)}-hez.`,
        )
        dialogsStore.handleClose()
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: FormEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.handleClose()
  }

  return (
    <DialogContent
      className="sm:max-w-md"
      showCloseButton={false}
      onEscapeKeyDown={dialogsStore.handleClose}
    >
      <form.AppForm>
        <form
          name="connect-to-tracker"
          className="grid gap-4"
          onSubmit={handleSubmit}
        >
          <DialogHeader>
            <DialogTitle>Csatlakozás a tracker-hez</DialogTitle>
            <DialogDescription>
              Válaszd ki a csatlakoztatni kívánt tracker-t és add meg a
              bejelentkezési adataidat.
            </DialogDescription>
          </DialogHeader>
          <form.Field name="tracker">
            {(field) => (
              <Field>
                <FieldLabel htmlFor={field.name}>Tracker</FieldLabel>
                <Select
                  value={field.state.value}
                  name={field.name}
                  onValueChange={(value: TrackerEnum) =>
                    field.handleChange(value)
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {inactiveTrackers.map((tracker) => (
                      <SelectItem key={tracker.value} value={tracker.value}>
                        {tracker.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            )}
          </form.Field>
          <form.AppField
            name="trackerUsn"
            children={(field) => <field.AppTextField label="Felhasználónév" />}
          />
          <form.AppField
            name="trackerPwd"
            children={(field) => (
              <field.AppTextField label="Jelszó" type="password" />
            )}
          />
          <DialogFooter>
            <form.SubscribeButton variant="outline" onClick={handleClose}>
              Mégsem
            </form.SubscribeButton>
            <form.SubscribeButton type="submit">
              Csatlakozás
            </form.SubscribeButton>
          </DialogFooter>
        </form>
      </form.AppForm>
    </DialogContent>
  )
}
