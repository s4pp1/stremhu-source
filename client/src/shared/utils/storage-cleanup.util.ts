import type {
  StorageCleanupProtectedReasonEnum,
  StorageCleanupScoreComponentKeyEnum,
} from '@/shared/lib/source/source-client'

export const STORAGE_CLEANUP_PROTECTED_REASON_LABELS: Record<
  StorageCleanupProtectedReasonEnum,
  string
> = {
  pinned: 'Rögzített',
  active_stream: 'Aktív stream',
  hnr_pending: "Hit'n'Run függő",
  hnr_unknown: "Hit'n'Run ismeretlen",
  keep_seed: 'Keep seed',
}

export const STORAGE_CLEANUP_SCORE_COMPONENT_LABELS: Record<
  StorageCleanupScoreComponentKeyEnum,
  string
> = {
  first_played: 'Első lejátszás óta',
  last_played: 'Utolsó lejátszás óta',
  downloaded: 'Letöltött méret',
  seeders: 'Seederek',
  leechers: 'Leechererek',
  uploaded: 'Feltöltött adat',
}
