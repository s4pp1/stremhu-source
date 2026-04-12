import { Validate } from 'class-validator';

import { IsIPv4 } from 'src/common/validators/is-ip-v4';

export class LocalUrlRequestDto {
  /** IPv4 cím a helyi URL generálásához */
  @Validate(IsIPv4)
  ipv4: string;
}
