import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import type { FormEventHandler, MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { TrackerEnum } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import {
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { getReferenceData } from '@/queries/reference-data'
import { useLoginTracker } from '@/queries/trackers'
import { useDialogsStore } from '@/store/dialogs-store'

interface AddTrackerContentProps {
  activeTrackers: Array<TrackerEnum>
}

const schema = z.object({
  tracker: z.enum(TrackerEnum),
  trackerUsn: z.string().nonempty('A felhasználónév kitöltése kötelező'),
  trackerPwd: z.string().nonempty('A jelszó kitöltése kötelező'),
})

export function AddTrackerContent(props: AddTrackerContentProps) {
  const { activeTrackers } = props

  const { handleClose } = useDialogsStore()

  const { data: referenceData } = useQuery(getReferenceData)
  if (!referenceData) throw new Error(`Nincs "reference-data" a cache-ben`)

  const { mutateAsync: loginTracker } = useLoginTracker()

  const {
    option: { trackers },
    labelMap,
  } = referenceData

  const inactiveTrackers = trackers.filter(
    (tracker) => !activeTrackers.includes(tracker.value),
  )

  const form = useForm({
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
          `Sikeres csatlakozás az ${labelMap.tracker[value.tracker]}-hez.`,
        )
        handleClose()
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

  const onClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    handleClose()
  }

  return (
    <form name="connect-to-tracker" className="grid gap-4" onSubmit={onSubmit}>
      <DialogHeader>
        <DialogTitle>Csatlakozás a tracker-hez</DialogTitle>
        <DialogDescription>
          Válaszd ki a csatlakoztatni kívánt tracker-t és add meg a
          bejelentkezési adataidat.
        </DialogDescription>
      </DialogHeader>
      <FieldGroup>
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
        <form.Field name="trackerUsn">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Felhasználónév</FieldLabel>
              <Input
                id={field.name}
                name={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
        <form.Field name="trackerPwd">
          {(field) => (
            <Field>
              <FieldLabel>Jelszó</FieldLabel>
              <Input
                id={field.name}
                name={field.name}
                type="password"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
              {field.state.meta.isTouched && (
                <FieldError errors={field.state.meta.errors} />
              )}
            </Field>
          )}
        </form.Field>
      </FieldGroup>
      <form.Subscribe selector={(state) => [state.isSubmitting]}>
        {([isSubmitting]) => (
          <DialogFooter>
            <Button variant="outline" disabled={isSubmitting} onClick={onClose}>
              Mégsem
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Csatlakozás
            </Button>
          </DialogFooter>
        )}
      </form.Subscribe>
    </form>
  )
}
