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

export class StreamDto {
  @ApiProperty()
  name: string;

  @ApiProperty()
  description: string;

  @ApiProperty()
  url: string;

  @ApiProperty({ type: BehaviorHintsDto })
  behaviorHints: BehaviorHintsDto;
}

export class StreamsResponseDto {
  @ApiProperty({ type: StreamDto, isArray: true })
  streams: StreamDto[];
}
