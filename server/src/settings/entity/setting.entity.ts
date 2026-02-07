import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('settings')
export class Setting {
  @PrimaryColumn({ type: 'text' })
  key: string;

  @Column({ type: 'simple-json', default: '{}' })
  value: Record<string, unknown>;
}
