import type { DragEndEvent } from '@dnd-kit/core'
import { DndContext } from '@dnd-kit/core'
import {
  restrictToVerticalAxis,
  restrictToWindowEdges,
} from '@dnd-kit/modifiers'
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import {
  BanIcon,
  GrabIcon,
  HeartIcon,
  SearchIcon,
  TrashIcon,
} from 'lucide-react'
import type { MouseEventHandler } from 'react'

import { SortableWrapper } from '@/shared/components/sortable-wrapper'
import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { Button } from '@/shared/components/ui/button'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import { withForm } from '@/shared/contexts/form-context'
import { useMetadata } from '@/shared/hooks/use-metadata'
import type { PreferenceItemDto } from '@/shared/queries/me-preferences'

import { PreferenceItem } from '../../routes/_protected/settings/preferences/-components/preference-item'
import { preferenceFormValues } from './preference-form-values'

export const PreferenceForm = withForm({
  defaultValues: preferenceFormValues,
  render: ({ form }) => {
    const { getPreference } = useMetadata()

    return (
      <div className="grid gap-8">
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
              <div className="grid gap-4">
                <div className="grid">
                  <ItemTitle>Elérhető tulajdonságok</ItemTitle>
                  <ItemDescription>
                    Ezeket a tulajdonságokat tudod preferálni vagy kizárni.
                  </ItemDescription>
                </div>
                <div className="grid gap-3">
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
            const onReorderItems = (event: DragEndEvent) => {
              const { active, over } = event
              if (!over || active.id === over.id) return

              const preferredItems = [...preferred] as Array<
                (typeof preferred)[number]
              >
              const oldIndex = preferredItems.findIndex(
                (value) => value === active.id,
              )
              const newIndex = preferredItems.findIndex(
                (value) => value === over.id,
              )
              if (oldIndex === -1 || newIndex === -1) return

              const reorderedItems = arrayMove(
                preferredItems,
                oldIndex,
                newIndex,
              )
              form.setFieldValue(
                'preferred',
                reorderedItems as PreferenceItemDto,
              )
            }

            return (
              <div className="grid gap-4">
                <Item className="p-0">
                  <ItemContent className="gap-0">
                    <ItemTitle>Preferált tulajdonságok</ItemTitle>
                    <ItemDescription>
                      Azok a tulajdonságok, amiket ide hozzáadsz előrébb
                      kerülnek a listában.
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <ItemMedia variant="icon" className="rounded-full">
                      <GrabIcon />
                    </ItemMedia>
                  </ItemActions>
                </Item>
                <div className="grid gap-3">
                  <DndContext
                    onDragEnd={onReorderItems}
                    modifiers={[restrictToVerticalAxis, restrictToWindowEdges]}
                  >
                    <SortableContext
                      items={preferred}
                      strategy={verticalListSortingStrategy}
                    >
                      {preferred.map((item) => {
                        const handleRemove: MouseEventHandler<
                          HTMLButtonElement
                        > = (event) => {
                          event.preventDefault()

                          const filteredItems = preferred.filter(
                            (i) => i !== item,
                          ) as PreferenceItemDto
                          form.setFieldValue('preferred', filteredItems)
                        }

                        return (
                          <SortableWrapper
                            key={item}
                            item={item}
                            resolveId={(i) => i}
                          >
                            <PreferenceItem
                              preference={preference}
                              preferenceItem={item}
                              actions={[
                                <Button
                                  key="delete"
                                  size="icon-sm"
                                  variant="destructive"
                                  className="rounded-full"
                                  onPointerDown={(event) =>
                                    event.stopPropagation()
                                  }
                                  onClick={handleRemove}
                                >
                                  <TrashIcon />
                                </Button>,
                              ]}
                            />
                          </SortableWrapper>
                        )
                      })}
                    </SortableContext>
                  </DndContext>
                  {preferred.length === 0 && (
                    <Alert>
                      <HeartIcon />
                      <AlertTitle>Nincs preferált tulajdonság</AlertTitle>
                    </Alert>
                  )}
                </div>
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
                <div className="grid gap-3">
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
              </div>
            )
          }}
        </form.Subscribe>
      </div>
    )
  },
})
