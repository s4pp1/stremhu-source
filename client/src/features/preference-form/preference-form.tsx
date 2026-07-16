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
import { GrabIcon, HeartIcon, SearchIcon, TrashIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'
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
import type { PreferenceResponse } from '@/shared/lib/source/source-client'

import { PreferenceItem } from '../../routes/_protected/settings/preferences/-components/preference-item'
import { preferenceFormValues } from './preference-form-values'

export const PreferenceForm = withForm({
  defaultValues: preferenceFormValues,
  props: {
    preference: {} as PreferenceResponse,
  },
  render: ({ form, preference }) => {
    return (
      <div className="grid gap-8">
        <form.Subscribe selector={(state) => state.values}>
          {(values) => {
            const availableAttributes = preference.attributes.filter(
              (attribute) => !values.attributeIds.includes(attribute.id),
            )

            return (
              <div className="grid gap-4">
                <div className="grid">
                  <ItemTitle><Trans>Available attributes</Trans></ItemTitle>
                  <ItemDescription>
                    <Trans>You can prefer or exclude these attributes.</Trans>
                  </ItemDescription>
                </div>
                <div className="grid gap-3">
                  {availableAttributes.map((attribute) => {
                    const handleAddPreferred: MouseEventHandler<
                      HTMLButtonElement
                    > = (event) => {
                      event.preventDefault()

                      const attributeIds = [
                        ...values.attributeIds,
                        attribute.id,
                      ]
                      form.setFieldValue('attributeIds', attributeIds)
                    }

                    return (
                      <PreferenceItem
                        key={attribute.id}
                        attribute={attribute}
                        actions={[
                          <Button
                            size="icon-sm"
                            className="rounded-full"
                            onClick={handleAddPreferred}
                          >
                            <HeartIcon />
                          </Button>,
                        ]}
                      />
                    )
                  })}
                  {availableAttributes.length === 0 && (
                    <Alert>
                      <SearchIcon />
                      <AlertTitle><Trans>No more available attributes.</Trans></AlertTitle>
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
            attributeIds: state.values.attributeIds,
          })}
        >
          {({ attributeIds }) => {
            const onReorderItems = (event: DragEndEvent) => {
              const { active, over } = event
              if (!over || active.id === over.id) return

              const preferredItems = [
                ...attributeIds,
              ] as (typeof attributeIds)[number][]
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
              form.setFieldValue('attributeIds', reorderedItems)
            }

            return (
              <div className="grid gap-4">
                <Item className="p-0">
                  <ItemContent className="gap-0">
                    <ItemTitle><Trans>Preferred attributes</Trans></ItemTitle>
                    <ItemDescription>
                      <Trans>The attributes you add here will appear higher in the list.</Trans>
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
                      items={attributeIds}
                      strategy={verticalListSortingStrategy}
                    >
                      {attributeIds.map((item) => {
                        const handleRemove: MouseEventHandler<
                          HTMLButtonElement
                        > = (event) => {
                          event.preventDefault()

                          const filteredItems = attributeIds.filter(
                            (i) => i !== item,
                          )
                          form.setFieldValue('attributeIds', filteredItems)
                        }

                        return (
                          <SortableWrapper
                            key={item}
                            item={item}
                            resolveId={(i) => i}
                          >
                            <PreferenceItem
                              attribute={
                                preference.attributes.find(
                                  (a) => a.id === item,
                                )!
                              }
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
                  {attributeIds.length === 0 && (
                    <Alert>
                      <HeartIcon />
                      <AlertTitle><Trans>No preferred attributes</Trans></AlertTitle>
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
