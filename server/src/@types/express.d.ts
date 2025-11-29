import { Request } from 'express';

import { User } from 'src/users/entity/user.entity';

declare module 'express' {
  export interface Request {
    user?: User | null;
  }
}
