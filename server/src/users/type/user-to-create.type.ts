import { UserRoleEnum } from '../enum/user-role.enum';

export interface UserToCreate {
  username: string;
  password: string | null;
  userRole: UserRoleEnum;
}
