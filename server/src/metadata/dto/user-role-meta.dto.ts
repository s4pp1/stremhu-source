import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { UserRoleEnum } from 'src/users/enum/user-role.enum';

export class UserRoleMetaDto {
  /** Felhasználói szerepkör értéke */
  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  value: UserRoleEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
