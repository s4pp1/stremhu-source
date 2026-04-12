import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';

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

  @Expose()
  @ApiProperty({ type: BehaviorHintsDto })
  behaviorHints: BehaviorHintsDto;
}

export class StremioStreamsResponseDto {
  @Expose()
  @ApiProperty({ type: StremioStreamDto, isArray: true })
  streams: StremioStreamDto[];
}
