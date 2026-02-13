import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { USER_ROLE_OPTIONS } from 'src/common/constant/user-role.constant';
import { AUDIO_QUALITY_OPTIONS } from 'src/preference-items/constant/audio-codec.constant';
import { LANGUAGE_OPTIONS } from 'src/preference-items/constant/language.constant';
import { RESOLUTION_OPTIONS } from 'src/preference-items/constant/resolution.constant';
import { SOURCE_OPTIONS } from 'src/preference-items/constant/source.constant';
import { VIDEO_QUALITY_OPTIONS } from 'src/preference-items/constant/video-quality.constant';
import { SettingsService } from 'src/settings/settings.service';
import { TrackersService } from 'src/trackers/trackers.service';

import { MetadataDto } from './dto/metadata.dto';

@Controller('/metadata')
@ApiTags('Metadata')
export class MetadataController {
  constructor(
    private readonly configService: ConfigService,
    private readonly settingsService: SettingsService,
    private readonly trackersService: TrackersService,
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
      audioQuality: AUDIO_QUALITY_OPTIONS,
      source: SOURCE_OPTIONS,
      languages: LANGUAGE_OPTIONS,
      trackers: this.trackersService.getTrackerOptionsWithUrl(),
      endpoint,
      version,
    };
  }
}
