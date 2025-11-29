import { ApiProperty } from '@nestjs/swagger';
import { Validate } from 'class-validator';

import { IsIPv4 } from 'src/common/validators/is-ip-v4';

export class LocalUrlRequestDto {
  @Validate(IsIPv4)
  @ApiProperty()
  ipv4: string;
}
