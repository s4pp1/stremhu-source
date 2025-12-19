import { ApiProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import { IsBoolean, IsDate, IsEnum, IsNumber, IsString } from 'class-validator';

import { IsNullable } from 'src/common/validators/is-nullable';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TrackerCredentialDto {
  @IsEnum(TrackerEnum)
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  @IsString()
  @ApiProperty()
  username: string;

  @Exclude()
  password: string;

  @IsNullable()
  @IsBoolean()
  @ApiProperty({ type: 'boolean', nullable: true })
  hitAndRun: boolean | null;

  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'integer', nullable: true })
  keepSeedSeconds: number | null;

  @IsDate()
  @ApiProperty()
  updatedAt: Date;

  @IsDate()
  @ApiProperty()
  createdAt: Date;
}
