import { ApiProperty } from '@nestjs/swagger';

export class ManifestBehaviorHintsDto {
  @ApiProperty()
  adult?: boolean | undefined;

  @ApiProperty()
  p2p?: boolean | undefined;

  @ApiProperty()
  configurable?: boolean;

  @ApiProperty()
  configurationRequired?: boolean;
}
