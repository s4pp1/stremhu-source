import { useForm } from '@tanstack/react-form'
import { useSuspenseQueries } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { capitalize } from 'lodash'
import { t } from '@lingui/core/macro'
import { Trans } from '@lingui/react/macro'
import {
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
import type { UserResponse } from '@/shared/lib/source/source-client'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'
import { getSystemRoles } from '@/shared/queries/system'
import { useUserDelete, useUserUpdate } from '@/shared/queries/users'

type UserProfileProps = {
  user: UserResponse
}

const schema = z.object({
  userRole: z.string(),
})

export function UserProfile(props: UserProfileProps) {
  const { user } = props

  const [{ data: me }, { data: roles }] = useSuspenseQueries({
    queries: [getMe(), getSystemRoles],
  })
  assertExists(me)

  const navigate = useNavigate()
  const confirmDialog = useConfirmDialog()
  const dialogs = useDialogs()

  const { mutateAsync: updateUser } = useUserUpdate()
  const { mutateAsync: deleteUser } = useUserDelete()

  const form = useForm({
    defaultValues: {
      userRole: user.role.id,
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
        await updateUser({
          userId: user.id,
          payload: {
            roleId: value.userRole,
          },
        })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleDeleteUser = async () => {
    await confirmDialog.confirm({
      title: t`Are you sure you want to delete?`,
      description: (
        <Trans>
          <span className="font-bold">{user.username}</span>'s deletion is permanent and cannot be undone!
        </Trans>
      ),
      onConfirm: async () => {
        await deleteUser(user.id)
        navigate({ to: '/dashboard/users' })
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><Trans>{user.username} user profile</Trans></CardTitle>
        <CardDescription><Trans>Edit user profile</Trans></CardDescription>
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
            <ItemTitle><Trans>Change username</Trans></ItemTitle>
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
            <ItemTitle><Trans>Change password</Trans></ItemTitle>
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
              <FieldLabel htmlFor={field.name}><Trans>Role</Trans></FieldLabel>
              <Select
                value={field.state.value}
                name={field.name}
                disabled={me.id === user.id}
                onValueChange={(value) => field.handleChange(value)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((userRole) => (
                    <SelectItem
                      key={userRole.id}
                      value={userRole.id}
                      className="first-letter:capitalize"
                    >
                      {capitalize(userRole.name)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}
        </form.Field>
      </CardContent>
    </Card>
  )
}
