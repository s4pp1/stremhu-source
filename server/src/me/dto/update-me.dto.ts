import { ApiProperty } from '@nestjs/swagger';
import { IsBoolean, IsNumber, IsOptional, IsString } from 'class-validator';

export class UpdateMeDto {
  @IsOptional()
  @IsString()
  @ApiProperty({
    type: 'string',
    required: false,
  })
  username?: string;

  @IsOptional()
  @IsString()
  @ApiProperty({
    type: 'string',
    required: false,
  })
  password?: string;

  @IsOptional()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true, required: false })
  torrentSeed?: number | null;

  @IsOptional()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', required: false })
  onlyBestTorrent?: boolean;
}
