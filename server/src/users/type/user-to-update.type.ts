import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserToUpdate {
  userRole?: UserRoleEnum;
  username?: string;
  password?: string | null;
  torrentSeed?: number | null;
  onlyBestTorrent?: boolean;
}
