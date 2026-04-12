import { ApiProperty } from '@nestjs/swagger';
import { Expose, Type } from 'class-transformer';
import { IsArray } from 'class-validator';

export class BehaviorHintsDto {
  @Expose()
  @ApiProperty()
  countryWhitelist?: string[];

  @Expose()
  @ApiProperty()
  notWebReady: boolean;

  @Expose()
  @ApiProperty()
  bingeGroup?: string;

  @Expose()
  @ApiProperty()
  filename?: string;
}

export class StremioStreamDto {
  @Expose()
  @ApiProperty()
  name: string;

  @Expose()
  @ApiProperty()
  description: string;

  @Expose()
  @ApiProperty()
  url: string;

  @Type(() => BehaviorHintsDto)
  @Expose()
  @ApiProperty({ type: BehaviorHintsDto })
  behaviorHints: BehaviorHintsDto;
}

export class StremioStreamsResponseDto {
  @IsArray()
  @Type(() => StremioStreamDto)
  @Expose()
  @ApiProperty({ type: StremioStreamDto, isArray: true })
  streams: StremioStreamDto[];
}
