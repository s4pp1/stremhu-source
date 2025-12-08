import { Link } from '@tanstack/react-router'

import { UserNavigation } from './user-navigation'

export function AppHeader() {
  return (
    <div className="sticky top-0 flex justify-center items-center w-full h-14 bg-card border-b shadow-sm z-50">
      <div className="flex justify-between items-center w-full max-w-3xl px-4">
        <Link to="/" className="flex items-center gap-2 font-medium">
          <img src="/logo.png" alt="StremHU" className="h-8 w-auto" />
          Source
        </Link>
        <UserNavigation />
      </div>
    </div>
  )
}
