import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
import _ from 'lodash'
import {
  CopyIcon,
  PencilIcon,
  ShieldUserIcon,
  TrashIcon,
  UserPenIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useConfirmDialog } from '@/features/confirm/use-confirm-dialog'
import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldLabel } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/shared/components/ui/input-group'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import type { UserDto } from '@/shared/lib/source-client'
import { UserRoleEnum } from '@/shared/lib/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'
import { getMetadata } from '@/shared/queries/metadata'
import { useDeleteUser, useUpdateProfile } from '@/shared/queries/users'

type UserProfile = {
  user: UserDto
}

const schema = z.object({
  userRole: z.enum(UserRoleEnum),
})

export function UserProfile(props: UserProfile) {
  const { user } = props

  const [{ data: metadata }, { data: me }] = useQueries({
    queries: [getMetadata, getMe],
  })
  if (!metadata) throw new Error(`Nincs "metadata" a cache-ben`)
  if (!me) throw new Error(`Nincs "me" a cache-ben`)

  const confirmDialog = useConfirmDialog()
  const dialogs = useDialogs()

  const { urlEndpoint } = useIntegrationDomain({
    stremioToken: user.stremioToken,
  })

  const { mutateAsync: updateProfile } = useUpdateProfile()
  const { mutateAsync: deleteUser } = useDeleteUser()

  const form = useForm({
    defaultValues: {
      userRole: user.userRole,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 2000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateProfile({ userId: user.id, payload: value })
        toast.success(`Sikeresen módosítva.`)
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(urlEndpoint)
      toast.success('URL kimásolva a vágólapra')
    } catch {
      toast.error('Másolás sikertelen')
    }
  }

  const handleDeleteUser = async () => {
    await confirmDialog.confirm({
      title: `Biztos törölni szeretnéd?`,
      description: `"${user.username}" törlése végleges és nem lehetséges visszaállítani!`,
      onConfirm: async () => {
        await deleteUser(user.id)
      },
    })
  }

  return (
    <Card className="break-inside-avoid mb-4">
      <CardHeader>
        <CardTitle>"{user.username}" felhasználó</CardTitle>
        <CardDescription>Felhasználó profiljának módosítása</CardDescription>
        {user.id !== me.id && (
          <CardAction>
            <Button
              size="icon-sm"
              variant="destructive"
              className="rounded-full"
              onClick={handleDeleteUser}
            >
              <TrashIcon />
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserPenIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Felhasználónév módosítása</ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({
                  type: 'CHANGE_USERNAME',
                  options: { user: user },
                })
              }
            >
              <PencilIcon />
            </Button>
          </ItemActions>
        </Item>
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <ShieldUserIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>Jelszó módosítása</ItemTitle>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              variant="default"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({
                  type: 'CHANGE_PASSWORD',
                  options: { user: user },
                })
              }
            >
              <PencilIcon />
            </Button>
          </ItemActions>
        </Item>
        <form.Field name="userRole">
          {(field) => (
            <Field>
              <FieldLabel htmlFor={field.name}>Jogosultság</FieldLabel>
              <Select
                value={field.state.value}
                name={field.name}
                disabled={me.id === user.id}
                onValueChange={(value: UserRoleEnum) =>
                  field.handleChange(value)
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {metadata.userRoles.map((userRole) => (
                    <SelectItem
                      key={userRole.value}
                      value={userRole.value}
                      className="first-letter:capitalize"
                    >
                      {_.capitalize(userRole.label)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}
        </form.Field>
        <Field>
          <FieldLabel htmlFor="stremioToken">Stremio addon URL</FieldLabel>
          <InputGroup>
            <InputGroupInput name="stremioToken" readOnly value={urlEndpoint} />
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                variant="ghost"
                size="icon-sm"
                onClick={handleCopyUrl}
              >
                <CopyIcon />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </CardContent>
    </Card>
  )
}
