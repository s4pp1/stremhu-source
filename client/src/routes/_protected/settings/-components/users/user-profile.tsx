import { useForm } from '@tanstack/react-form'
import { useQueries } from '@tanstack/react-query'
import _ from 'lodash'
import {
  CopyIcon,
  PencilIcon,
  ShieldUserIcon,
  TrashIcon,
  UserIcon,
  UserPenIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { UserDto } from '@/client/app-client'
import { UserRoleEnum } from '@/client/app-client'
import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useIntegrationDomain } from '@/hooks/use-integration-domain'
import { useReferenceDataOptionLabel } from '@/hooks/use-reference-data-option-label'
import { getMe } from '@/queries/me'
import { getReferenceData } from '@/queries/reference-data'
import { useDeleteUser, useUpdateProfile } from '@/queries/users'
import { useConfirmDialogStore } from '@/store/confirm-dialog-store'
import { DialogEnum, useDialogs } from '@/store/dialogs-store'

interface UserProfileProps {
  user: UserDto
}

const schema = z.object({
  userRole: z.enum(UserRoleEnum),
})

export function UserProfile(props: UserProfileProps) {
  const { user } = props

  const [{ data: referenceData }, { data: me }] = useQueries({
    queries: [getReferenceData, getMe],
  })
  if (!referenceData) throw new Error(`Nincs "referenceData" a cache-ben`)
  if (!me) throw new Error(`Nincs "me" a cache-ben`)

  const { getUserRoleLabel } = useReferenceDataOptionLabel()
  const { confirm } = useConfirmDialogStore()
  const { handleOpen } = useDialogs()

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
    const ok = await confirm({
      title: `Biztos törölni szeretnéd?`,
      description: `"${user.username}" törlése végleges és nem lehetséges visszaállítani!`,
    })
    if (!ok) return

    await deleteUser(user.id)
  }

  return (
    <Card className="break-inside-avoid mb-4">
      <CardHeader>
        <CardTitle>Bejelentkezés és biztonság</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Item variant="default" className="p-0">
          <ItemMedia variant="icon">
            <UserIcon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>{user.username}</ItemTitle>
            <ItemDescription>
              {getUserRoleLabel(user.userRole)} jogosultság
            </ItemDescription>
          </ItemContent>
          {user.id !== me.id && (
            <ItemActions>
              <Button
                size="icon-sm"
                variant="destructive"
                className="rounded-full"
                onClick={handleDeleteUser}
              >
                <TrashIcon />
              </Button>
            </ItemActions>
          )}
        </Item>
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
                handleOpen({
                  dialog: DialogEnum.CHANGE_USERNAME_DIALOG,
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
                handleOpen({
                  dialog: DialogEnum.CHANGE_PASSWORD_DIALOG,
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
                onValueChange={(value: UserRoleEnum) =>
                  field.handleChange(value)
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {referenceData.option.userRoles.map((userRole) => (
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
