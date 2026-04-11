import { ApiProperty } from '@nestjs/swagger';
import { IsUUID } from 'class-validator';

export class PairStatusRequestDto {
  @ApiProperty()
  @IsUUID()
  deviceCode: string;
}
