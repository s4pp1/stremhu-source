import { Link, useMatches } from '@tanstack/react-router'
import { Fragment } from 'react/jsx-runtime'

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/shared/components/ui/breadcrumb'

export function SettingsBreadcrumb() {
  const matches = useMatches()

  const breadcrumbItems = matches
    .filter((match) => match.loaderData?.breadcrumb)
    .map(({ pathname, loaderData }) => ({
      href: pathname,
      label: loaderData?.breadcrumb,
    }))

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {breadcrumbItems.map((breadcrumbItem, index) => (
          <Fragment key={breadcrumbItem.href}>
            {index > 0 && <BreadcrumbSeparator />}
            <BreadcrumbItem>
              {index + 1 === breadcrumbItems.length ? (
                <BreadcrumbPage>{breadcrumbItem.label}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink asChild>
                  <Link to={breadcrumbItem.href}>{breadcrumbItem.label}</Link>
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
          </Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}
