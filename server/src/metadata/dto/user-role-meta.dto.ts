import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { UserRoleEnum } from 'src/users/enum/user-role.enum';

export class UserRoleMetaDto {
  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  value: UserRoleEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
