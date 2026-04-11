import { ApiProperty } from '@nestjs/swagger';

export class PairInitDto {
  @ApiProperty()
  userCode: string;

  @ApiProperty()
  deviceCode: string;

  @ApiProperty()
  expiresAt: Date;
}
