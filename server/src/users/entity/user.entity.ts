import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

import { UserRoleEnum } from '../enum/user-role.enum';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ unique: true })
  username: string;

  @Column({ name: 'password_hash', type: 'text', nullable: true })
  passwordHash: string | null;

  @Index()
  @Column({ name: 'token', type: 'uuid' })
  token: string;

  @Column({
    name: 'user_role',
    type: 'simple-enum',
    enum: UserRoleEnum,
  })
  userRole: UserRoleEnum;

  @Column({
    name: 'torrent_seed',
    type: 'integer',
    nullable: true,
    default: null,
  })
  torrentSeed: number | null;

  @Column({ name: 'only_best_torrent', type: 'boolean', default: false })
  onlyBestTorrent!: boolean;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
