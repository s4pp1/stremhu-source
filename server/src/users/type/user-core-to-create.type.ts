import { UserRoleEnum } from '../enum/user-role.enum';

export type UserCoreToCreate = {
  username: string;
  passwordHash: string | null;
  userRole: UserRoleEnum;
  token: string;
};
