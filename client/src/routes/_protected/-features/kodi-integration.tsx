import { useSuspenseQueries } from '@tanstack/react-query'
import { CopyIcon, LinkIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'

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
import { getSystemStatus } from '@/shared/queries/system'

export function KodiIntegration() {
  const [{ data: systemStatus }] = useSuspenseQueries({
    queries: [getSystemStatus],
  })

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
          <Trans>During the StremHU addon login process, the following URL must be entered.</Trans>
        </p>
        <Field className="max-w-sm">
          <InputGroup>
            <InputGroupInput value={systemStatus.appUrl} />
            <InputGroupAddon align="inline-start">
              <LinkIcon />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton onClick={() => handleCopy(systemStatus.appUrl)}>
                <CopyIcon />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </CardContent>
    </Card>
  )
}
