import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import {
  LANGUAGE_OPTIONS,
  RESOLUTION_OPTIONS,
  USER_ROLE_OPTIONS,
  VIDEO_QUALITY_OPTIONS,
} from 'src/common/common.constant';
import { SettingsStore } from 'src/settings/core/settings.store';
import { TRACKER_OPTIONS } from 'src/trackers/trackers.constants';

import { MetadataDto } from './dto/metadata.dto';

@Controller('/metadata')
@ApiTags('Metadata')
export class MetadataController {
  constructor(
    private readonly configService: ConfigService,
    private readonly settingsStore: SettingsStore,
  ) {}

  @Get('/')
  @ApiResponse({ status: 200, type: MetadataDto })
  async metadata(): Promise<MetadataDto> {
    const version = this.configService.getOrThrow<string>('app.version');
    const endpoint = await this.settingsStore.getEndpoint();

    return {
      userRoles: USER_ROLE_OPTIONS,
      resolutions: RESOLUTION_OPTIONS,
      videoQualities: VIDEO_QUALITY_OPTIONS,
      languages: LANGUAGE_OPTIONS,
      trackers: TRACKER_OPTIONS,
      endpoint,
      version,
    };
  }
}
