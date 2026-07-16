import { LanguagesIcon } from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import { useLanguageStore } from '@/shared/hooks/useLanguageStore'
import { locales } from '@/shared/i18n'

export function LanguageSwitcher() {
  const { locale, setLocale } = useLanguageStore()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" className="rounded-full">
          <LanguagesIcon />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-32">
        {Object.entries(locales).map(([code, name]) => (
          <DropdownMenuItem
            key={code}
            onClick={() => setLocale(code)}
            disabled={locale === code}
          >
            {name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
