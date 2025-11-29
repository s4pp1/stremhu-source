import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('settings')
export class Setting {
  @PrimaryColumn({ type: 'text' })
  id!: string;

  @Column({
    name: 'enebled_local_ip',
    type: 'boolean',
    default: true,
  })
  enebledlocalIp!: boolean;

  @Column({ type: 'text', nullable: true, default: null })
  address!: string | null;

  @Column({ name: 'download_limit', type: 'integer', default: -1 })
  downloadLimit!: number;

  @Column({ name: 'upload_limit', type: 'integer', default: -1 })
  uploadLimit!: number;

  @Column({ name: 'hit_and_run', type: 'boolean', default: false })
  hitAndRun!: boolean;

  @Column({ name: 'cache_retention', type: 'text', nullable: true })
  cacheRetention!: string | null;

  @Column({ name: 'catalog_token', type: 'text', nullable: true })
  catalogToken!: string | null;
}
