import { useSuspenseQueries } from '@tanstack/react-query'
import { GlobeIcon, HouseIcon, ToolboxIcon } from 'lucide-react'

import { Alert, AlertDescription } from '@/shared/components/ui/alert'
import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { withForm } from '@/shared/contexts/form-context'
import { getNetworkProviders } from '@/shared/queries/network'
import { getSystemStatus } from '@/shared/queries/system'

import { networkAccessDefaultValues } from './network-access.defaults'

export const UrlConfiguration = withForm({
  defaultValues: networkAccessDefaultValues,
  render: ({ form }) => {
    const [{ data: providers }, { data: systemStatus }] = useSuspenseQueries({
      queries: [getNetworkProviders, getSystemStatus],
    })

    return (
      <form.Subscribe
        selector={(state) => {
          const mode = state.values.mode
          const providerId = mode === 'auto' ? state.values.provider : undefined
          return { mode, providerId }
        }}
      >
        {({ mode, providerId }) => {
          const selectedProvider = providers.find(
            (provider) => provider.id === providerId,
          )

          if (mode === 'none') return null

          if (mode === 'local') {
            return (
              <div className="grid gap-4">
                <Separator />
                <Alert>
                  <HouseIcon />
                  <AlertDescription className="inline">
                    A{' '}
                    <a
                      href="https://local-ip.medicmobile.org"
                      target="_blank"
                      className="link-primary"
                    >
                      https://local-ip.medicmobile.org
                    </a>{' '}
                    segítségével lesz elérhető a szerver a helyi hálózatodon,
                    így nincs szükség további beállítások megadására.
                  </AlertDescription>
                </Alert>
              </div>
            )
          }

          return (
            <div className="grid gap-4">
              <Separator />

              <form.Field name="host">
                {(field) => (
                  <Field>
                    <FieldLabel>Domain</FieldLabel>
                    <Input
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                    />
                    {field.state.meta.isTouched && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )}
              </form.Field>

              {mode === 'auto' && (
                <>
                  <form.Field name="token">
                    {(field) => (
                      <Field>
                        <FieldLabel>Token / API kulcs</FieldLabel>
                        <Input
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                        />
                        {field.state.meta.isTouched && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )}
                  </form.Field>

                  <form.Field name="email">
                    {(field) => (
                      <Field>
                        <FieldLabel>E-mail cím</FieldLabel>
                        <Input
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          type="email"
                        />
                        {field.state.meta.isTouched && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )}
                  </form.Field>

                  <form.Field name="connection">
                    {(field) => (
                      <div className="grid gap-1">
                        <Label
                          htmlFor={field.name}
                          className="flex items-start gap-3"
                        >
                          <p className="flex-1 text-sm leading-none font-medium">
                            Külső elérés bekapcsolása
                          </p>
                          <Switch
                            id={field.name}
                            checked={field.state.value === 'public'}
                            onCheckedChange={(checked) => {
                              field.setValue(checked ? 'public' : 'local')
                            }}
                          />
                        </Label>
                        <p className="text-muted-foreground text-sm">
                          Publikus IPv4 cimmel kell rendelkezned és a routeren
                          nyitva kell legyen a{' '}
                          <span className="font-bold">{systemStatus.port}</span>
                          -es port!
                        </p>
                      </div>
                    )}
                  </form.Field>
                  <Alert>
                    <ToolboxIcon />
                    <AlertDescription className="inline">
                      A {selectedProvider?.name} használatához látogass el a{' '}
                      <a
                        href={selectedProvider?.websiteUrl}
                        target="_blank"
                        className="link-primary"
                      >
                        {selectedProvider?.websiteUrl}
                      </a>{' '}
                      oldalra, és regisztrálj egy ingyenes fiókot.
                    </AlertDescription>
                  </Alert>
                </>
              )}

              {mode === 'manual' && (
                <Alert>
                  <GlobeIcon />
                  <AlertDescription className="inline">
                    A beállítást követően a szerver a{' '}
                    <span className="font-bold">
                      http://
                      {systemStatus.hostIp}:{systemStatus.port}
                    </span>{' '}
                    címen lesz elérhető, ha a Reverse Proxy konfiguráció nem
                    működik.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )
        }}
      </form.Subscribe>
    )
  },
})
