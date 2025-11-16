import { ApiProperty } from '@nestjs/swagger';

import { UserDto } from 'src/users/dto/user.dto';

export class MeUserDto {
  @ApiProperty({ type: UserDto, nullable: true })
  me: UserDto | null;
}
