import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { USER_ROLE_OPTIONS } from 'src/common/constant/user-role.constant';
import { SettingsService } from 'src/settings/settings.service';
import { TrackersMetaService } from 'src/trackers/meta/trackers-meta.service';

import { MetadataDto } from './dto/metadata.dto';
import { PreferencesMetadataService } from './preferences-metadata.service';

@Injectable()
export class MetadataService {
  constructor(
    private readonly configService: ConfigService,
    private readonly settingsService: SettingsService,
    private readonly trackersMetaService: TrackersMetaService,
    private readonly preferencesMetadataService: PreferencesMetadataService,
  ) {}

  async get(): Promise<MetadataDto> {
    const endpoint = await this.getEndpoint();
    const preferences = await this.preferencesMetadataService.get();

    return {
      version: this.getVersion(),
      endpoint: endpoint,
      userRoles: this.getUserRoles(),
      trackers: this.getTrackers(),
      preferences: preferences,
    };
  }

  getVersion() {
    const version = this.configService.getOrThrow<string>('app.version');
    return version;
  }

  async getEndpoint() {
    const endpoint = await this.settingsService.getEndpoint();
    return endpoint;
  }

  getUserRoles() {
    return USER_ROLE_OPTIONS;
  }

  getTrackers() {
    const trackers = this.trackersMetaService.all();
    return trackers;
  }
}
