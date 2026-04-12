import { IsNumber, IsOptional } from 'class-validator';

export class UpdateExternalSettingDto {
  /** Port azonosító */
  @IsOptional()
  @IsNumber()
  port?: number;
}
