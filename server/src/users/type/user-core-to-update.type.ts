import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserCoreToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  passwordHash?: string | null;
  torrentSeed?: number | null;
  token?: string;
  onlyBestTorrent?: boolean;
}
