import { Column, Entity, Index, PrimaryColumn } from 'typeorm';

@Entity('sessions')
@Index(['expires'])
export class Session {
  @PrimaryColumn({ type: 'text' })
  sid!: string;

  @Column({ type: 'text' })
  data!: string;

  @Column({ type: 'integer' })
  expires!: number;
}
