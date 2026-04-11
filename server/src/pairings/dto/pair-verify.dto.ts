import { ApiProperty } from '@nestjs/swagger';

export class PairVerifyDto {
  @ApiProperty()
  success: boolean;
}
