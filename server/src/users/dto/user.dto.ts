import { Resolution } from '@ctrl/video-filename-parser';
import { ApiProperty } from '@nestjs/swagger';
import { Exclude } from 'class-transformer';
import {
  ArrayUnique,
  IsArray,
  IsBoolean,
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
  IsUUID,
} from 'class-validator';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { IsNullable } from 'src/common/validators/is-nullable';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

export class UserDto {
  @IsUUID()
  @ApiProperty({ format: 'uuid' })
  id: string;

  @IsString()
  @ApiProperty()
  username: string;

  @Exclude()
  @IsOptional()
  @IsString()
  passwordHash: string | null;

  @IsString()
  @ApiProperty()
  token: string;

  @IsEnum(UserRoleEnum)
  @ApiProperty({ enum: UserRoleEnum, enumName: 'UserRoleEnum' })
  userRole: UserRoleEnum;

  @IsArray()
  @ArrayUnique()
  @IsEnum(Resolution, { each: true })
  @ApiProperty({ enum: Resolution, enumName: 'ResolutionEnum', isArray: true })
  torrentResolutions: Resolution[];

  @IsArray()
  @ArrayUnique()
  @IsEnum(VideoQualityEnum, { each: true })
  @ApiProperty({
    enum: VideoQualityEnum,
    enumName: 'VideoQualityEnum',
    isArray: true,
  })
  torrentVideoQualities: VideoQualityEnum[];

  @IsArray()
  @ArrayUnique()
  @IsEnum(LanguageEnum, { each: true })
  @ApiProperty({ enum: LanguageEnum, enumName: 'LanguageEnum', isArray: true })
  torrentLanguages: LanguageEnum[];

  @IsNullable()
  @IsNumber()
  @ApiProperty({ type: 'number', nullable: true })
  torrentSeed: number | null;

  @IsBoolean()
  @ApiProperty({ type: 'boolean' })
  onlyBestTorrent: boolean;
}
