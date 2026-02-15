import { BanIcon, HeartIcon, SearchIcon, TrashIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'

import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { Button } from '@/shared/components/ui/button'
import { ItemDescription, ItemTitle } from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { withForm } from '@/shared/contexts/form-context'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type { PreferenceItemDto } from '@/shared/queries/me-preferences'

import { PreferenceItem } from '../../-components/preference-item'
import { preferenceFormValues } from './preference-form-values'

export const PreferenceForm = withForm({
  defaultValues: preferenceFormValues,
  render: ({ form }) => {
    const { getPreference } = useMetadata()

    return (
      <div className="grid gap-6">
        <form.Subscribe selector={(state) => state.values}>
          {(values) => {
            const preference = getPreference(values.preference)
            const preferenceItems = preference.items

            const availablePreferenceItems = preferenceItems.filter(
              (preferenceItem) =>
                ![...values.preferred, ...values.blocked].includes(
                  preferenceItem.value,
                ),
            )

            return (
              <div className="grid gap-2">
                <div className="grid">
                  <ItemTitle>Elérhető tulajdonságok</ItemTitle>
                  <ItemDescription>
                    Ezeket a tulajdonságokat tudod preferálni vagy kizárni.
                  </ItemDescription>
                </div>

                {availablePreferenceItems.map((item) => {
                  const handleAddPreferred: MouseEventHandler<
                    HTMLButtonElement
                  > = (event) => {
                    event.preventDefault()

                    const items = [
                      ...values.preferred,
                      item.value,
                    ] as PreferenceItemDto
                    form.setFieldValue('preferred', items)
                  }

                  const handleAddBlocked: MouseEventHandler<
                    HTMLButtonElement
                  > = (event) => {
                    event.preventDefault()

                    const items = [
                      ...values.blocked,
                      item.value,
                    ] as PreferenceItemDto
                    form.setFieldValue('blocked', items)
                  }

                  return (
                    <PreferenceItem
                      key={item.value}
                      preference={values.preference}
                      preferenceItem={item.value}
                      actions={[
                        <Button
                          size="icon-sm"
                          className="rounded-full"
                          onClick={handleAddPreferred}
                        >
                          <HeartIcon />
                        </Button>,
                        <Button
                          size="icon-sm"
                          variant="destructive"
                          className="rounded-full"
                          onClick={handleAddBlocked}
                        >
                          <BanIcon />
                        </Button>,
                      ]}
                    />
                  )
                })}
                {availablePreferenceItems.length === 0 && (
                  <Alert>
                    <SearchIcon />
                    <AlertTitle>Nincs több elérhető tulajdonság.</AlertTitle>
                  </Alert>
                )}
              </div>
            )
          }}
        </form.Subscribe>
        <Separator />
        <form.Subscribe
          selector={(state) => ({
            preference: state.values.preference,
            preferred: state.values.preferred,
          })}
        >
          {({ preference, preferred }) => {
            return (
              <div className="grid gap-4">
                <div className="grid">
                  <ItemTitle>Preferált tulajdonságok</ItemTitle>
                  <ItemDescription>
                    Azok a tulajdonságok, amiket ide hozzáadsz előrébb kerülnek
                    a listában.
                  </ItemDescription>
                </div>
                {preferred.map((item) => {
                  const handleRemove: MouseEventHandler<HTMLButtonElement> = (
                    event,
                  ) => {
                    event.preventDefault()

                    const filteredItems = preferred.filter(
                      (i) => i !== item,
                    ) as PreferenceItemDto
                    form.setFieldValue('preferred', filteredItems)
                  }

                  return (
                    <PreferenceItem
                      key={item}
                      preference={preference}
                      preferenceItem={item}
                      actions={[
                        <Button
                          size="icon-sm"
                          variant="destructive"
                          className="rounded-full"
                          onClick={handleRemove}
                        >
                          <TrashIcon />
                        </Button>,
                      ]}
                    />
                  )
                })}
                {preferred.length === 0 && (
                  <Alert>
                    <HeartIcon />
                    <AlertTitle>Nincs preferált tulajdonság</AlertTitle>
                  </Alert>
                )}
              </div>
            )
          }}
        </form.Subscribe>
        <Separator />
        <form.Subscribe
          selector={(state) => ({
            preference: state.values.preference,
            blocked: state.values.blocked,
          })}
        >
          {({ preference, blocked }) => {
            return (
              <div className="grid gap-4">
                <div className="grid">
                  <ItemTitle>Kizárt tulajdonságok</ItemTitle>
                  <ItemDescription>
                    Azok a tulajdonságok, amiket ide hozzáadsz nem fognak
                    megjelennie.
                  </ItemDescription>
                </div>
                {blocked.map((item) => {
                  const handleRemove: MouseEventHandler<HTMLButtonElement> = (
                    event,
                  ) => {
                    event.preventDefault()

                    const filteredItems = blocked.filter(
                      (i) => i !== item,
                    ) as PreferenceItemDto
                    form.setFieldValue('blocked', filteredItems)
                  }

                  return (
                    <PreferenceItem
                      key={item}
                      preference={preference}
                      preferenceItem={item}
                      actions={[
                        <Button
                          size="icon-sm"
                          variant="destructive"
                          className="rounded-full"
                          onClick={handleRemove}
                        >
                          <TrashIcon />
                        </Button>,
                      ]}
                    />
                  )
                })}
                {blocked.length === 0 && (
                  <Alert>
                    <BanIcon />
                    <AlertTitle>Nincs kizárt tulajdonság</AlertTitle>
                  </Alert>
                )}
              </div>
            )
          }}
        </form.Subscribe>
      </div>
    )
  },
})
