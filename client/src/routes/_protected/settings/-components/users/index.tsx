import { useQuery } from '@tanstack/react-query'
import { PlusIcon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/shared/components/ui/accordion'
import { Button } from '@/shared/components/ui/button'
import { useMetadataLabel } from '@/shared/hooks/use-metadata-label'
import { getUsers } from '@/shared/queries/users'

import { UserPreferences } from './user-preferences'
import { UserProfile } from './user-profile'

export function Users() {
  const { data: users } = useQuery(getUsers)
  if (!users) throw new Error(`Nincs "users" a cache-ben`)

  const { getUserRoleLabel } = useMetadataLabel()
  const dialogs = useDialogs()

  return (
    <div className="grid gap-4">
      <div className="grid gap-2">
        <div className="flex gap-4 justify-between items-center">
          <h3 className="text-2xl font-medium tracking-tight">Felhasználók</h3>
          <Button
            size="sm"
            onClick={() => dialogs.openDialog({ type: 'ADD_USER' })}
          >
            <PlusIcon />
            Új fiók
          </Button>
        </div>
        <p className="text-muted-foreground">
          Kezeld a felhasználókat, szerepköröket és hozzáféréseket.
        </p>
      </div>
      <Accordion
        type="single"
        collapsible
        className="w-full"
        defaultValue="item-1"
      >
        {users.map((user) => (
          <AccordionItem key={user.id} value={user.id}>
            <AccordionTrigger className="text-lg">
              <div className="text-lg">
                {user.username}{' '}
                <span className="text-sm text-muted-foreground">
                  ({getUserRoleLabel(user.userRole)})
                </span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="columns-1 md:columns-2">
              <UserProfile user={user} />
              <UserPreferences user={user} />
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  )
}
