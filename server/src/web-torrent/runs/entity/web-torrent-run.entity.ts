import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryColumn,
  Unique,
  UpdateDateColumn,
} from 'typeorm';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

@Entity('web_torrent_runs')
@Unique('unique_web_torrent_run_tracker_torrent', ['tracker', 'torrentId'])
export class WebTorrentRun {
  @PrimaryColumn({ type: 'simple-enum', enum: TrackerEnum })
  tracker!: TrackerEnum;

  @PrimaryColumn({ name: 'torrent_id' })
  torrentId!: string;

  @PrimaryColumn({ name: 'info_hash', unique: true })
  infoHash!: string;

  @Column({ name: 'imdb_id' })
  imdbId!: string;

  @Column({ type: 'integer', default: 0 })
  uploaded: number;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
