import { Expose } from 'class-transformer';
import { IsNumber, IsOptional } from 'class-validator';

export class UpdateExternalSettingDto {
  /** Port azonosító */
  @IsOptional()
  @IsNumber()
  @Expose()
  port?: number;
}
