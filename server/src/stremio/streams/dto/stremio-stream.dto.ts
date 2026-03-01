import { ApiProperty } from '@nestjs/swagger';

export class BehaviorHintsDto {
  @ApiProperty()
  countryWhitelist?: string[];

  @ApiProperty()
  notWebReady: boolean;

  @ApiProperty()
  bingeGroup?: string;

  @ApiProperty()
  filename?: string;
}

export class StremioStreamDto {
  @ApiProperty()
  name: string;

  @ApiProperty()
  description: string;

  @ApiProperty()
  url: string;

  @ApiProperty({ type: BehaviorHintsDto })
  behaviorHints: BehaviorHintsDto;
}

export class StremioStreamsResponseDto {
  @ApiProperty({ type: StremioStreamDto, isArray: true })
  streams: StremioStreamDto[];
}
