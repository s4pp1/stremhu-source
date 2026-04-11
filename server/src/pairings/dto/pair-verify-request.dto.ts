import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class PairVerifyRequestDto {
  @ApiProperty()
  @IsString()
  userCode: string;
}
