import * as z from 'zod'

export const torrentSeedSchema = z.number().nullable()
export const onlyBestTorrentSchema = z.boolean()
