import { ApiProperty } from '@nestjs/swagger';

import { UserDto } from 'src/users/dto/user.dto';

export class MeDto {
  @ApiProperty({ type: UserDto, nullable: true })
  me: UserDto | null;
}
