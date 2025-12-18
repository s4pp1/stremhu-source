import { Injectable, OnApplicationBootstrap } from '@nestjs/common';
import { Cron, CronExpression, SchedulerRegistry } from '@nestjs/schedule';

import { SettingsStore } from 'src/settings/core/settings.store';
import { TorrentsService } from 'src/torrents/torrents.service';

import { TrackersStore } from './core/trackers.store';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';
import { TrackerAdapter } from './tracker.types';

@Injectable()
export class TrackerMaintenanceService implements OnApplicationBootstrap {
  constructor(
    private readonly schedulerRegistry: SchedulerRegistry,
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly trackersStore: TrackersStore,
    private readonly torrentsService: TorrentsService,
    private readonly settingsStore: SettingsStore,
  ) {}

  async onApplicationBootstrap() {
    const setting = await this.settingsStore.findOneOrThrow();
    const job = this.schedulerRegistry.getCronJob('cleanupTorrents');

    if (!setting.hitAndRun) {
      await job.stop();
    }
  }

  async setHitAndRunCron(enabled: boolean): Promise<void> {
    const job = this.schedulerRegistry.getCronJob('cleanupTorrents');

    if (enabled && !job.isActive) {
      job.start();
    }

    if (!enabled && job.isActive) {
      await job.stop();
    }
  }

  @Cron(CronExpression.EVERY_DAY_AT_4AM, { name: 'cleanupTorrents' })
  async cleanupHitAndRun(): Promise<void> {
    const credentials = await this.trackersStore.find();
    await Promise.all(
      credentials.map((credential) => {
        const adapter = this.trackerAdapterRegistry.get(credential.tracker);
        return this.cleanupHitAndRunTracker(adapter);
      }),
    );
  }

  private async cleanupHitAndRunTracker(adapter: TrackerAdapter) {
    const seedReqTorrentIds = await adapter.seedRequirement();
    await this.torrentsService.purgeTrackerExcept(
      adapter.tracker,
      seedReqTorrentIds,
    );
  }
}
