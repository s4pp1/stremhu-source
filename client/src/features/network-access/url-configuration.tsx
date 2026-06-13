import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { withForm } from '@/shared/contexts/form-context'

import { networkAccessDefaultValues } from './network-access.defaults'

export const UrlConfiguration = withForm({
  defaultValues: networkAccessDefaultValues,
  render: ({ form }) => {
    return (
      <form.Subscribe selector={(state) => [state.values.mode]}>
        {([mode]) => {
          if (mode === 'none') return null

          if (mode === 'local') return null

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
                      placeholder="Pl.: stremhu.duckdns.org"
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
                          placeholder="Szolgáltatótól kapott token / api kulcs"
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
                          placeholder="SSL tanúsítvány generálásához"
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
                          Csak akkor lehetséges, ha nem vagy CGNAT mögött és a
                          routeren kinyitod a megfelelő portot!
                        </p>
                      </div>
                    )}
                  </form.Field>
                </>
              )}

              {mode === 'manual' && (
                <p className="text-muted-foreground text-sm">
                  Reverse Proxy használata esetén http protokkolon lehet elérni
                  a szervert. Ellenkező esetben biztosítanod kell a certeket.
                </p>
              )}
            </div>
          )
        }}
      </form.Subscribe>
    )
  },
})
