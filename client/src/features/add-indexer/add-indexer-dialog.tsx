import { useSuspenseQueries } from '@tanstack/react-query'
import type { MouseEventHandler, SubmitEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import { Checkbox } from '@/shared/components/ui/checkbox'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Field, FieldLabel } from '@/shared/components/ui/field'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { useAppForm } from '@/shared/contexts/form-context'
import type { IndexerDefinitionResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import {
  getIndexerDefinitions,
  useIndexerLogin,
} from '@/shared/queries/indexers'

import type { AddIndexerDialog } from './add-indexer.types'

const schema = z
  .object({
    indexer: z.custom<IndexerDefinitionResponse>(
      (val) => Boolean(val && typeof val === 'object'),
      'A torrent oldal kiválasztása kötelező',
    ),
    username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
    password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
    useTotp: z.boolean(),
    totpSecret: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.useTotp && !data.totpSecret.trim()) {
      ctx.addIssue({
        code: 'custom',
        message: 'A 2FA titkos kulcs kitöltése kötelező',
        path: ['totpSecret'],
      })
    }
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
      indexer: inactiveIndexers[0],
      username: '',
      password: '',
      useTotp: false,
      totpSecret: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await loginIndexer({
          indexerId: value.indexer.id,
          username: value.username,
          password: value.password,
          totpSecret:
            value.indexer.supportsTotp &&
            value.useTotp &&
            value.totpSecret.trim()
              ? value.totpSecret.trim()
              : null,
        })
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
            <form.Field name="indexer">
              {(field) => (
                <Field>
                  <FieldLabel htmlFor={field.name}>Torrent oldal</FieldLabel>
                  <Select
                    value={field.state.value.id}
                    name={field.name}
                    onValueChange={(id) => {
                      const selected = inactiveIndexers.find((i) => i.id === id)
                      if (selected) {
                        form.reset()
                        field.setValue(selected)
                      }
                    }}
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
            <form.Subscribe
              selector={(state) =>
                [state.values.indexer, state.values.useTotp] as const
              }
            >
              {([indexer, useTotp]) => {
                if (!indexer.supportsTotp) return null

                return (
                  <div className="flex flex-col gap-3">
                    <form.Field name="useTotp">
                      {(field) => (
                        <Field orientation="horizontal">
                          <Checkbox
                            id={field.name}
                            name={field.name}
                            checked={field.state.value}
                            onCheckedChange={(checked) => {
                              field.handleChange(Boolean(checked))
                              if (!checked) {
                                form.setFieldValue('totpSecret', '')
                              }
                            }}
                          />
                          <Label htmlFor={field.name}>
                            Kétlépcsős azonosítás (2FA / TOTP) használata
                          </Label>
                        </Field>
                      )}
                    </form.Field>
                    {useTotp && (
                      <form.AppField
                        name="totpSecret"
                        children={(field) => (
                          <field.AppTextField
                            label="2FA titkos kulcs (TOTP)"
                            description="Csak az alkalmazás alapú (pl. Google Authenticator, Authy) kétlépcsős azonosítás (2FA) támogatott. Add meg a 2FA beállításakor kapott titkos kulcsot (a QR kód alatt szokott lenni). Ha már be van állítva, a hitelesítő alkalmazásodból is kinyerhető (pl. QR kód exportálással), vagy az adott oldalon a 2FA kikapcsolásával és újbóli bekapcsolásával ismét megszerezheted."
                          />
                        )}
                      />
                    )}
                  </div>
                )
              }}
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
