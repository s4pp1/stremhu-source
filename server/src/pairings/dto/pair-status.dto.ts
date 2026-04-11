import { ApiProperty } from '@nestjs/swagger';

export class PairStatusDto {
  @ApiProperty()
  status: string;

  @ApiProperty({ required: false })
  token?: string;
}
