import { useSuspenseQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { BanIcon, CircleIcon } from 'lucide-react'
import type { MouseEventHandler } from 'react'

import { PreferenceItem } from '@/routes/_protected/settings/preferences/-components/preference-item'
import { Alert, AlertTitle } from '@/shared/components/ui/alert'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { ItemDescription, ItemTitle } from '@/shared/components/ui/item'
import { Separator } from '@/shared/components/ui/separator'
import {
  getUserAttributeExclusions,
  getUserAttributes,
  useUserAddAttributeToExclusion,
  useUserRemoveAttributeFromExclusion,
} from '@/shared/queries/users'

export const Route = createFileRoute(
  '/_protected/dashboard/users/$userId/preferences/attributes/',
)({
  component: RouteComponent,
})

function RouteComponent() {
  const { userId } = Route.useParams()

  const [{ data: attributes }, { data: exclusions }] = useSuspenseQueries({
    queries: [getUserAttributes(userId), getUserAttributeExclusions(userId)],
  })

  const { mutate: addAttributeToExclusion } =
    useUserAddAttributeToExclusion(userId)
  const { mutate: removeAttributeFromExclusion } =
    useUserRemoveAttributeFromExclusion(userId)

  const handleAddToExclusion =
    (attributeId: string): MouseEventHandler<HTMLButtonElement> =>
    (event) => {
      event.preventDefault()
      event.stopPropagation()

      addAttributeToExclusion({ attributeId })
    }

  const handleRemoveFromExclusion =
    (attributeId: string): MouseEventHandler<HTMLButtonElement> =>
    (event) => {
      event.preventDefault()
      event.stopPropagation()

      removeAttributeFromExclusion(attributeId)
    }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Kizárt tulajdonságok konfigurációja</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-8">
        <div className="grid gap-4">
          <div className="grid">
            <ItemTitle>Kizárt tulajdonságok</ItemTitle>
            <ItemDescription>
              A kliensekben megjelenő listában nem fognak szerepelni azok a
              torrent-ek, amik tartalmaznák a kizárt tulajdonságot.
            </ItemDescription>
          </div>
          {exclusions.map((exclusion) => (
            <PreferenceItem
              key={exclusion.id}
              attribute={exclusion}
              actions={[
                <Button
                  key="delete"
                  size="icon-sm"
                  className="rounded-full"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={handleRemoveFromExclusion(exclusion.id)}
                >
                  <CircleIcon />
                </Button>,
              ]}
            />
          ))}
          {exclusions.length === 0 && (
            <Alert>
              <BanIcon />
              <AlertTitle>Nincs kizárt tulajdonság.</AlertTitle>
            </Alert>
          )}
        </div>
        <Separator />
        <div className="grid gap-4">
          <div className="grid">
            <ItemTitle>Kizárható tulajdonságok</ItemTitle>
            <ItemDescription>
              Ezek a tulajdonságok kizárhatók, amiknek az a hatása, hogy a
              kliensek listázójában nem fognak megjelenni a kizárt
              tulajdonsággal rendelkező torrentek.
            </ItemDescription>
          </div>
          {attributes.map((attribute) => (
            <PreferenceItem
              key={attribute.id}
              attribute={attribute}
              actions={[
                <Button
                  key="add"
                  size="icon-sm"
                  variant="destructive"
                  className="rounded-full"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={handleAddToExclusion(attribute.id)}
                >
                  <BanIcon />
                </Button>,
              ]}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
