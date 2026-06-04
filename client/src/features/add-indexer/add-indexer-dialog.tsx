import { useSuspenseQueries } from '@tanstack/react-query'
import type { MouseEventHandler, SubmitEventHandler } from 'react'
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
import { Field, FieldLabel } from '@/shared/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import {
  getIndexerDefinitions,
  useIndexerLogin,
} from '@/shared/queries/indexers'

import type { AddIndexerDialog } from './add-indexer.types'

const schema = z.object({
  indexerId: z.string(),
  username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
  password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
})

export function AddIndexerDialog(dialog: OpenedDialog & AddIndexerDialog) {
  const [{ data: indexerDefinitions }] = useSuspenseQueries({
    queries: [getIndexerDefinitions],
  })

  const { activeIndexerIds } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: loginIndexer } = useIndexerLogin()

  const inactiveTrackers = indexerDefinitions.filter(
    (indexer) => !activeIndexerIds.includes(indexer.id),
  )

  const form = useAppForm({
    defaultValues: {
      indexerId: '',
      username: '',
      password: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await loginIndexer(value)
        dialogsStore.closeDialog(dialog.id)
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
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
            <form.Field name="indexerId">
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={field.name}>Tracker</FieldLabel>
                  <Select
                    value={field.state.value}
                    name={field.name}
                    onValueChange={(value) => field.handleChange(value)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {inactiveTrackers.map((indexer) => (
                        <SelectItem key={indexer.id} value={indexer.id}>
                          {indexer.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
            <form.AppField
              name="username"
              children={(field) => (
                <field.AppTextField label="Felhasználónév" />
              )}
            />
            <form.AppField
              name="password"
              children={(field) => (
                <field.AppTextField label="Jelszó" type="password" />
              )}
            />
            <DialogFooter>
              <form.SubscribeButton
                variant="outline"
                type="button"
                onClick={handleClose}
              >
                Mégsem
              </form.SubscribeButton>
              <form.SubscribeButton type="submit">
                Csatlakozás
              </form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
