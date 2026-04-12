import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { UserRoleEnum } from 'src/users/enum/user-role.enum';

export class UserRoleMetaDto {
  /** Felhasználói szerepkör értéke */
  @Expose()
  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  value: UserRoleEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
