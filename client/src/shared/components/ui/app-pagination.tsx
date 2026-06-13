import type { LinkProps } from '@tanstack/react-router'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from './pagination'

type MakeLink = (page: number) => Pick<LinkProps, 'to' | 'search'>

type AppPagination = {
  page: number
  limit: number
  total: number
  makeLink: MakeLink
}

export function AppPagination(props: AppPagination) {
  const { page, limit, total, makeLink } = props

  const totalPages = Math.max(1, Math.ceil(total / limit))
  const clampedPage = Math.min(Math.max(page, 1), totalPages)

  const windowSize = Math.min(3, totalPages)
  const start = Math.max(
    1,
    Math.min(clampedPage - 1, totalPages - windowSize + 1),
  )
  const pages = Array.from({ length: windowSize }, (_, i) => start + i)

  const prevDisabled = clampedPage === 1
  const nextDisabled = clampedPage === totalPages

  return (
    <Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationLink
            {...makeLink(clampedPage - 1)}
            disabled={prevDisabled}
          >
            <ChevronLeftIcon />
          </PaginationLink>
        </PaginationItem>

        {start > 1 && (
          <>
            <PaginationItem>
              <PaginationLink {...makeLink(1)}>1</PaginationLink>
            </PaginationItem>
            {start > 2 && (
              <PaginationItem>
                <PaginationEllipsis />
              </PaginationItem>
            )}
          </>
        )}

        {pages.map((p) => (
          <PaginationItem key={p}>
            <PaginationLink {...makeLink(p)} isActive={p === clampedPage}>
              {p}
            </PaginationLink>
          </PaginationItem>
        ))}

        {start + windowSize - 1 < totalPages && (
          <>
            {start + windowSize - 1 < totalPages - 1 && (
              <PaginationItem>
                <PaginationEllipsis />
              </PaginationItem>
            )}
            <PaginationItem>
              <PaginationLink {...makeLink(totalPages)}>
                {totalPages}
              </PaginationLink>
            </PaginationItem>
          </>
        )}

        <PaginationItem>
          <PaginationLink
            {...makeLink(clampedPage + 1)}
            disabled={nextDisabled}
          >
            <ChevronRightIcon />
          </PaginationLink>
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  )
}
