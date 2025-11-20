import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('settings')
export class Setting {
  @PrimaryColumn({ type: 'text' })
  id!: string;

  @Column({
    name: 'enebled_local_ip',
    type: 'boolean',
    default: false,
  })
  enebledlocalIp!: boolean;

  @Column({ type: 'text' })
  endpoint!: string;

  @Column({ name: 'upload_limit', type: 'integer', default: -1 })
  uploadLimit!: number;

  @Column({ name: 'hit_and_run', type: 'boolean', default: true })
  hitAndRun!: boolean;

  @Column({ name: 'cache_retention', type: 'text', nullable: true })
  cacheRetention!: string | null;

  @Column({ name: 'catalog_token', type: 'text', nullable: true })
  catalogToken!: string | null;
}
