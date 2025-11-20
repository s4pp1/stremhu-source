import { Inject, Injectable, Logger } from '@nestjs/common';

import { SettingsStore } from 'src/settings/core/settings.store';

import { CATALOG_CLIENT } from './catalog-client.token';
import { GetEpisodeImdbId } from './catalog-client.types';
import { CatalogClient } from './client';

@Injectable()
export class CatalogClientService {
  private readonly logger = new Logger(CatalogClientService.name);

  constructor(
    @Inject(CATALOG_CLIENT) private readonly client: CatalogClient,
    private settingsStore: SettingsStore,
  ) {}

  async getEpisodeImdbId(payload: GetEpisodeImdbId): Promise<string> {
    if (payload.season !== 0) {
      return payload.imdbId;
    }

    const { catalogToken } = await this.settingsStore.findOneOrThrow();

    if (!catalogToken) {
      return payload.imdbId;
    }

    try {
      const { episodeImdbId } =
        await this.client.imdb.imdbResolverControllerResolveSpecial(
          catalogToken,
          {
            episodeNumber: payload.episode,
            imdbId: payload.imdbId,
          },
        );

      return episodeImdbId;
    } catch {
      this.logger.error(
        `🛑 A catalog token nem megfelelő vagy a service nem érhető el.`,
      );
      return payload.imdbId;
    }
  }
}
