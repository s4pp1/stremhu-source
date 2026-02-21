import { ApiProperty } from '@nestjs/swagger';

export class MetaTrailerDto {
  @ApiProperty()
  ytId: string;

  @ApiProperty()
  description: string;
}
