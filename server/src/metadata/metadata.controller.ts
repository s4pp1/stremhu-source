import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { LANGUAGE_OPTIONS } from 'src/common/constant/language.constant';
import { RESOLUTION_OPTIONS } from 'src/common/constant/resolution.constant';
import { SOURCE_TYPE_OPTIONS } from 'src/common/constant/source-type.constant';
import { USER_ROLE_OPTIONS } from 'src/common/constant/user-role.constant';
import { VIDEO_QUALITY_OPTIONS } from 'src/common/constant/video-quality.constant';
import { SettingsService } from 'src/settings/settings.service';
import { TRACKER_OPTIONS } from 'src/trackers/trackers.constants';

import { MetadataDto } from './dto/metadata.dto';

@Controller('/metadata')
@ApiTags('Metadata')
export class MetadataController {
  constructor(
    private readonly configService: ConfigService,
    private readonly settingsService: SettingsService,
  ) {}

  @Get('/')
  @ApiResponse({ status: 200, type: MetadataDto })
  async metadata(): Promise<MetadataDto> {
    const version = this.configService.getOrThrow<string>('app.version');
    const endpoint = await this.settingsService.getEndpoint();

    return {
      userRoles: USER_ROLE_OPTIONS,
      resolutions: RESOLUTION_OPTIONS,
      videoQualities: VIDEO_QUALITY_OPTIONS,
      sourceTypes: SOURCE_TYPE_OPTIONS,
      languages: LANGUAGE_OPTIONS,
      trackers: TRACKER_OPTIONS,
      endpoint,
      version,
    };
  }
}
