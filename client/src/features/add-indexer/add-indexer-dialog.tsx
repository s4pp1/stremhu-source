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
import {
  Field,
  FieldDescription,
  FieldLabel,
} from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
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
  totp: z.string(),
})

export function AddIndexerDialog(dialog: OpenedDialog & AddIndexerDialog) {
  const [{ data: indexerDefinitions }] = useSuspenseQueries({
    queries: [getIndexerDefinitions],
  })

  const { activeIndexerIds } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: loginIndexer } = useIndexerLogin()

  const inactiveIndexers = indexerDefinitions.filter(
    (indexer) => !activeIndexerIds.includes(indexer.id),
  )

  const form = useAppForm({
    defaultValues: {
      indexerId: inactiveIndexers[0]?.id ?? '',
      username: '',
      password: '',
      totp: '',
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
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>Bejelentkezés a torrent oldalra</DialogTitle>
              <DialogDescription>
                Válaszd ki a bejelentkezni kívánt torrent oldalt és add meg az
                adataidat.
              </DialogDescription>
            </DialogHeader>
            <form.Field name="indexerId">
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={field.name}>Torrent oldal</FieldLabel>
                  <Select
                    value={field.state.value}
                    name={field.name}
                    onValueChange={(value) => field.handleChange(value)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {inactiveIndexers.map((indexer) => (
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
            <form.Subscribe selector={(state) => state.values.indexerId}>
              {(indexerId) =>
                indexerId === 'ncore' ? (
                  <form.Field name="totp">
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor={field.name}>
                          2FA titkos kulcs (TOTP)
                        </FieldLabel>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                        />
                        <FieldDescription>
                          Opcionális. Ha az nCore fiókodon be van kapcsolva a
                          kétlépcsős azonosítás (2FA), add meg a 2FA titkos
                          kulcsot. A kulcsot az nCore oldalon a{' '}
                          <span className="font-semibold">
                            Beállítások -&gt; Biztonság
                          </span>{' '}
                          menüpontban találod a QR kód alatt (a kód csak a 2FA
                          bekapcsolásakor látható, ha nincs meg, akkor ki, majd
                          újra be kell kapcsolni a 2FA-t).
                        </FieldDescription>
                      </Field>
                    )}
                  </form.Field>
                ) : null
              }
            </form.Subscribe>
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
