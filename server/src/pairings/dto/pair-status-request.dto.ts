import { IsUUID } from 'class-validator';

export class PairStatusRequestDto {
  @IsUUID()
  deviceCode: string;
}
