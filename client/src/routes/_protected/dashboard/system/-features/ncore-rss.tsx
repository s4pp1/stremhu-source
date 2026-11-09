import { useQuery } from '@tanstack/react-query'
import { RefreshCwIcon, SaveIcon, TrashIcon } from 'lucide-react'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Input } from '@/shared/components/ui/input'
import { Separator } from '@/shared/components/ui/separator'
import { parseApiError } from '@/shared/lib/utils'
import {
  getNcoreRssItems,
  getNcoreRssStatus,
  useNcoreRssAddManualItem,
  useNcoreRssClearFeed,
  useNcoreRssConfigureFeed,
  useNcoreRssSync,
  useNcoreRssUpdateItem,
} from '@/shared/queries/ncore-rss'

export function NcoreRss() {
  const {
    data: status,
    isError: statusError,
    isPending: statusPending,
  } = useQuery(getNcoreRssStatus)
  const { data: items = [], isPending: itemsPending } = useQuery({
    ...getNcoreRssItems,
    enabled: Boolean(status?.ncoreConnected),
  })
  const [feedUrl, setFeedUrl] = useState('')
  const [title, setTitle] = useState('')
  const [imdbId, setImdbId] = useState('')
  const [downloadUrl, setDownloadUrl] = useState('')
  const [edits, setEdits] = useState<
    Record<string, { imdbId: string; downloadUrl: string }>
  >({})

  const configureFeed = useNcoreRssConfigureFeed()
  const clearFeed = useNcoreRssClearFeed()
  const syncFeed = useNcoreRssSync()
  const addManualItem = useNcoreRssAddManualItem()
  const updateItem = useNcoreRssUpdateItem()

  const handleConfigureFeed = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!feedUrl.trim()) return
    try {
      await configureFeed.mutateAsync({ feedUrl: feedUrl.trim() })
      setFeedUrl('')
      toast.success('Az nCore RSS feed mentve és beolvasva.')
    } catch (error) {
      toast.error(parseApiError(error))
    }
  }

  const handleClearFeed = async () => {
    try {
      await clearFeed.mutateAsync()
      toast.success('Az automatikus RSS-frissítés kikapcsolva.')
    } catch (error) {
      toast.error(parseApiError(error))
    }
  }

  const handleSync = async () => {
    try {
      await syncFeed.mutateAsync()
      toast.success('Az nCore RSS feed frissítve.')
    } catch (error) {
      toast.error(parseApiError(error))
    }
  }

  const handleManualAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    try {
      await addManualItem.mutateAsync({
        title: title.trim(),
        imdbId: imdbId.trim(),
        downloadUrl: downloadUrl.trim(),
      })
      setTitle('')
      setImdbId('')
      setDownloadUrl('')
      toast.success('A torrent hozzáadva az IMDb-címhez.')
    } catch (error) {
      toast.error(parseApiError(error))
    }
  }

  const handleSaveItem = async (
    torrentId: string,
    currentImdbId: string | null,
    currentDownloadUrl: string | null,
  ) => {
    const draft = edits[torrentId]
    if (!draft) return
    const nextImdbId = draft.imdbId.trim()
    const nextDownloadUrl = draft.downloadUrl.trim()
    const payload: { imdbId?: string | null; downloadUrl?: string | null } = {}
    if (nextImdbId !== (currentImdbId ?? '')) {
      payload.imdbId = nextImdbId || null
    }
    if (nextDownloadUrl !== (currentDownloadUrl ?? '')) {
      payload.downloadUrl = nextDownloadUrl || null
    }
    if (Object.keys(payload).length === 0) return
    try {
      await updateItem.mutateAsync({
        torrentId,
        payload,
      })
      setEdits((current) => {
        const next = { ...current }
        delete next[torrentId]
        return next
      })
      toast.success('A feed elem javítva.')
    } catch (error) {
      toast.error(parseApiError(error))
    }
  }

  const ncoreReady = status?.ncoreConnected ?? false

  return (
    <Card>
      <CardHeader>
        <CardTitle>nCore RSS és kézi kiegészítés</CardTitle>
        <CardDescription>
          Az új feed elemeket a rendszer beolvassa, az IMDb-azonosítókat
          felismeri, és a találatokat megjeleníti a StremHU forrásai között.
          Ha egy cím nem felismerhető, itt kézzel hozzárendelheted.
        </CardDescription>
      </CardHeader>
      <Separator />
      <CardContent className="grid gap-6">
        {statusPending ? (
          <p className="text-muted-foreground text-sm">Állapot betöltése…</p>
        ) : statusError ? (
          <p className="text-destructive text-sm">
            Az nCore RSS állapotát nem sikerült betölteni.
          </p>
        ) : !ncoreReady ? (
          <p className="text-muted-foreground text-sm">
            Előbb jelentkezz be az nCore fiókoddal a Torrent oldalak kártyán.
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant={status?.configured ? 'secondary' : 'outline'}>
                {status?.configured ? 'RSS beállítva' : 'RSS nincs beállítva'}
              </Badge>
              <span className="text-muted-foreground">
                {status?.totalItems ?? 0} elem · {status?.unresolvedItems ?? 0}{' '}
                IMDb-azonosító nélkül
              </span>
              {status?.lastSyncedAt && (
                <span className="text-muted-foreground">
                  Utolsó frissítés:{' '}
                  {new Date(status.lastSyncedAt).toLocaleString()}
                </span>
              )}
            </div>

            <form className="grid gap-3" onSubmit={handleConfigureFeed}>
              <label className="grid gap-1.5 text-sm font-medium">
                nCore RSS hivatkozás
                <Input
                  type="url"
                  placeholder="https://ncore.pro/rss.php?..."
                  value={feedUrl}
                  onChange={(event) => setFeedUrl(event.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                />
              </label>
              <p className="text-muted-foreground text-xs">
                A hivatkozás titkos adatokat is tartalmazhat; a rendszer nem
                jeleníti meg újra. Mentéskor a feed első beolvasása is lefut.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!feedUrl.trim() || configureFeed.isPending}>
                  <SaveIcon />
                  Feed mentése
                </Button>
                {status?.configured && (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleSync}
                      disabled={syncFeed.isPending}
                    >
                      <RefreshCwIcon className={syncFeed.isPending ? 'animate-spin' : undefined} />
                      Frissítés most
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleClearFeed}
                      disabled={clearFeed.isPending}
                    >
                      <TrashIcon />
                      RSS kikapcsolása
                    </Button>
                  </>
                )}
              </div>
            </form>

            <Separator />

            <form className="grid gap-3" onSubmit={handleManualAdd}>
              <div>
                <h3 className="font-medium">Torrent kézi hozzárendelése</h3>
                <p className="text-muted-foreground text-sm">
                  Ha egy címet nem talált meg a keresés, add meg az nCore
                  torrent letöltési linkjét és az IMDb-azonosítót.
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Input
                  placeholder="Torrent címe"
                  aria-label="Torrent címe"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                />
                <Input
                  placeholder="IMDb azonosító, például tt1234567"
                  aria-label="IMDb azonosító"
                  value={imdbId}
                  onChange={(event) => setImdbId(event.target.value)}
                  required
                />
              </div>
              <Input
                type="url"
                placeholder="https://ncore.pro/torrents.php?action=download&id=12345"
                aria-label="nCore torrent letöltési link"
                value={downloadUrl}
                onChange={(event) => setDownloadUrl(event.target.value)}
                required
              />
              <div>
                <Button type="submit" disabled={addManualItem.isPending}>
                  Hozzáadás
                </Button>
              </div>
            </form>

            <Separator />

            <div className="grid gap-3">
              <div>
                <h3 className="font-medium">Beolvasott torrentek</h3>
                <p className="text-muted-foreground text-sm">
                  A kézi IMDb-azonosító felülírja az automatikusan felismertet.
                  A letöltési link is javítható.
                </p>
              </div>
              {itemsPending ? (
                <p className="text-muted-foreground text-sm">Betöltés…</p>
              ) : items.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  Még nincs beolvasott torrent. Állítsd be az RSS feedet vagy
                  adj hozzá egy torrentet kézzel.
                </p>
              ) : (
                <div className="grid max-h-[36rem] gap-3 overflow-y-auto pr-1">
                  {items.map((item) => {
                    const draft = edits[item.torrentId]
                    const shownImdbId =
                      draft?.imdbId ?? item.manualImdbId ?? item.imdbId ?? ''
                    const shownDownloadUrl =
                      draft?.downloadUrl ?? item.downloadUrl ?? ''

                    return (
                      <article
                        key={item.torrentId}
                        className="grid gap-2 rounded-lg border p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="min-w-0">
                            <p className="break-words font-medium">{item.title}</p>
                            <p className="text-muted-foreground text-xs">
                              nCore #{item.torrentId}
                              {item.detectedImdbId &&
                                ` · automatikusan: ${item.detectedImdbId}`}
                              {item.isManual && ' · kézi felvitel'}
                            </p>
                          </div>
                          {item.manualImdbId && (
                            <Badge variant="secondary">kézzel javítva</Badge>
                          )}
                        </div>
                        <div className="grid gap-2 md:grid-cols-[1fr_2fr_auto]">
                          <Input
                            aria-label={`${item.title} IMDb-azonosítója`}
                            placeholder="tt1234567"
                            value={shownImdbId}
                            onChange={(event) =>
                              setEdits((current) => ({
                                ...current,
                                [item.torrentId]: {
                                  imdbId: event.target.value,
                                  downloadUrl:
                                    current[item.torrentId]?.downloadUrl ??
                                    item.downloadUrl ??
                                    '',
                                },
                              }))
                            }
                          />
                          <Input
                            type="url"
                            aria-label={`${item.title} letöltési linkje`}
                            placeholder="nCore letöltési link"
                            value={shownDownloadUrl}
                            onChange={(event) =>
                              setEdits((current) => ({
                                ...current,
                                [item.torrentId]: {
                                  imdbId:
                                    current[item.torrentId]?.imdbId ??
                                    item.manualImdbId ??
                                    item.imdbId ??
                                    '',
                                  downloadUrl: event.target.value,
                                },
                              }))
                            }
                          />
                          <Button
                            type="button"
                            variant="outline"
                            disabled={updateItem.isPending || !draft}
                            onClick={() =>
                              void handleSaveItem(
                                item.torrentId,
                                item.manualImdbId ?? item.imdbId,
                                item.downloadUrl,
                              )
                            }
                          >
                            <SaveIcon />
                            Mentés
                          </Button>
                        </div>
                      </article>
                    )
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
