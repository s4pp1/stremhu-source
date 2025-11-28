import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber, IsString } from 'class-validator';

export class SettingDto {
  @IsBoolean()
  @ApiProperty()
  enebledlocalIp: boolean;

  @IsString()
  @ApiProperty()
  address: string;

  @IsNumber()
  @ApiProperty()
  downloadLimit: number;

  @IsNumber()
  @ApiProperty()
  uploadLimit: number;

  @IsBoolean()
  @ApiProperty()
  hitAndRun: boolean;

  @IsString()
  @ApiProperty({ nullable: true })
  cacheRetention: string | null;

  @IsString()
  @ApiProperty({ nullable: true })
  catalogToken: string | null;
}
