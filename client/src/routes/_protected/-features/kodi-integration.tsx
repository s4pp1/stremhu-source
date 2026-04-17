import { useSuspenseQueries } from '@tanstack/react-query'
import { CopyIcon, LinkIcon } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/shared/components/ui/input-group'
import { useCopy } from '@/shared/hooks/use-copy'
import { getMetadata } from '@/shared/queries/metadata'

export function KodiIntegration() {
  const [{ data: metadata }] = useSuspenseQueries({ queries: [getMetadata] })

  const { handleCopy } = useCopy()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Kodi</CardTitle>
        <CardDescription>
          <a className="link-primary" href="https://kodi.tv/" target="_blank">
            https://kodi.tv
          </a>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm text-muted-foreground">
          StremHU addon bejelentkezés folyamatánál a következő URL-t kell
          megadni.
        </p>
        <Field className="max-w-sm">
          <InputGroup>
            <InputGroupInput value={metadata.endpoint} />
            <InputGroupAddon align="inline-start">
              <LinkIcon />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton onClick={() => handleCopy(metadata.endpoint)}>
                <CopyIcon />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </CardContent>
    </Card>
  )
}
