import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';

import { User } from '../../users/entity/user.entity';
import { PairingStatus } from '../enum/pairing-status.enum';

@Entity('pairings')
export class Pairing {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Index()
  @Column({ name: 'user_code', type: 'text' })
  userCode: string;

  @Index()
  @Column({ name: 'device_code', type: 'uuid' })
  deviceCode: string;

  @Column({
    type: 'simple-enum',
    enum: PairingStatus,
    default: PairingStatus.PENDING,
  })
  status: PairingStatus;

  @Column({ name: 'user_id', type: 'uuid', nullable: true })
  userId: string | null;

  @ManyToOne(() => User, { nullable: true, onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User | null;

  @Column({ name: 'expires_at', type: 'datetime' })
  expiresAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
