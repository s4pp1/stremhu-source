import { useQuery } from '@tanstack/react-query'
import { CopyIcon, KeyIcon, LinkIcon } from 'lucide-react'

import {
  Card,
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
import { useCopy } from '@/shared/hooks/use-copy'
import { useIntegrationDomain } from '@/shared/hooks/use-integration-domain'
import { assertExists } from '@/shared/lib/utils'
import { getMe } from '@/shared/queries/me'

export function TorznabIntegration() {
  const { data: me } = useQuery(getMe())
  assertExists(me)

  const { torznabUrl } = useIntegrationDomain({
    apiKey: me.apiKey,
  })

  const { handleCopy } = useCopy()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Torznab</CardTitle>
        <CardDescription>
          <a
            className="link-primary"
            href="https://github.com/Viren070/AIOStreams"
            target="_blank"
          >
            AIOStreams, Prowlarr, Sonarr, Radarr
          </a>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm text-muted-foreground">
          Torznab indexerként add hozzá a klienshez az alábbi URL-t és API
          kulcsot.
        </p>
        <Field>
          <FieldLabel>Torznab URL</FieldLabel>
          <InputGroup>
            <InputGroupInput value={torznabUrl} readOnly />
            <InputGroupAddon align="inline-start">
              <LinkIcon />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton onClick={() => handleCopy(torznabUrl)}>
                <CopyIcon />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
        <Field>
          <FieldLabel>API kulcs</FieldLabel>
          <InputGroup>
            <InputGroupInput value={me.apiKey} readOnly type="password" />
            <InputGroupAddon align="inline-start">
              <KeyIcon />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton onClick={() => handleCopy(me.apiKey)}>
                <CopyIcon />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </CardContent>
    </Card>
  )
}
