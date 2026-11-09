import { useQuery } from '@tanstack/react-query'
import {
  ArrowUpIcon,
  CheckIcon,
  FolderIcon,
  FolderPlusIcon,
  HardDriveIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Input } from '@/shared/components/ui/input'
import { Spinner } from '@/shared/components/ui/spinner'
import { parseApiError } from '@/shared/lib/utils'
import {
  getBrowseDirectories,
  useCreateDirectory,
} from '@/shared/queries/filesystem'

interface DirectoryPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialPath?: string
  onSelect: (path: string) => void
}

export function DirectoryPickerDialog({
  open,
  onOpenChange,
  initialPath,
  onSelect,
}: DirectoryPickerDialogProps) {
  const [currentPath, setCurrentPath] = useState<string | undefined>(
    initialPath,
  )
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')

  const { data, isLoading, error } = useQuery({
    ...getBrowseDirectories(currentPath),
    enabled: open,
  })

  const { mutateAsync: createDirectory, isPending: isCreating } =
    useCreateDirectory()

  const activePath = data?.currentPath ?? currentPath ?? ''

  const handleSelect = () => {
    if (activePath) {
      onSelect(activePath)
      onOpenChange(false)
    }
  }

  const handleCreateDirectory = async () => {
    const trimmed = newFolderName.trim()
    if (!trimmed || !activePath) return

    try {
      const res = await createDirectory({
        parentPath: activePath,
        name: trimmed,
      })
      toast.success('Mappa sikeresen létrehozva!')
      setNewFolderName('')
      setShowNewFolder(false)
      setCurrentPath(res.path)
    } catch (err) {
      toast.error(parseApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl flex flex-col max-h-[85vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HardDriveIcon className="size-5 text-primary" />
            Letöltési mappa kiválasztása
          </DialogTitle>
          <DialogDescription>
            Böngéssz a könyvtárak között és válaszd ki a kívánt letöltési
            mappát.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 flex-1 min-h-0">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              disabled={!data?.parentPath || isLoading}
              onClick={() => {
                if (data?.parentPath) {
                  setCurrentPath(data.parentPath)
                }
              }}
              title="Egy szinttel feljebb"
            >
              <ArrowUpIcon className="size-4" />
            </Button>
            <div className="font-mono text-xs bg-muted/60 px-3 py-1.5 rounded-md border flex-1 break-all select-all">
              {activePath || 'Betöltés...'}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowNewFolder((prev) => !prev)}
            >
              <FolderPlusIcon className="size-4 mr-1" />
              Új mappa
            </Button>
          </div>

          {showNewFolder && (
            <div className="flex items-center gap-2 p-2 rounded-md bg-muted/40 border">
              <Input
                placeholder="Új mappa neve..."
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleCreateDirectory()
                  }
                }}
                disabled={isCreating}
                autoFocus
              />
              <Button
                type="button"
                size="sm"
                onClick={handleCreateDirectory}
                disabled={isCreating || !newFolderName.trim()}
              >
                {isCreating ? <Spinner className="size-4" /> : 'Létrehozás'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowNewFolder(false)
                  setNewFolderName('')
                }}
              >
                Mégsem
              </Button>
            </div>
          )}

          <div className="border rounded-md flex-1 min-h-[220px] max-h-[320px] overflow-y-auto divide-y divide-border/50">
            {isLoading ? (
              <div className="flex items-center justify-center h-full p-8 text-muted-foreground gap-2">
                <Spinner className="size-4" />
                <span>Mappák beolvasása...</span>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full p-8 text-destructive text-sm text-center">
                Nem sikerült beolvasni a könyvtárat.
              </div>
            ) : data?.directories && data.directories.length > 0 ? (
              data.directories.map((dir) => (
                <div
                  key={dir.path}
                  role="button"
                  tabIndex={0}
                  className="flex items-center gap-2.5 px-3 py-2 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors text-sm select-none"
                  onClick={() => setCurrentPath(dir.path)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setCurrentPath(dir.path)
                    }
                  }}
                >
                  <FolderIcon className="size-4 text-primary shrink-0" />
                  <span className="truncate flex-1 font-medium">
                    {dir.name}
                  </span>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center h-full p-8 text-muted-foreground text-sm">
                Nincsenek almappák ebben a könyvtárban
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Mégsem
          </Button>
          <Button
            type="button"
            onClick={handleSelect}
            disabled={!activePath || isLoading}
          >
            <CheckIcon className="size-4 mr-1.5" />
            Kiválasztás
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
