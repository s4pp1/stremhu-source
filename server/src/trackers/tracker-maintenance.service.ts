import { Injectable } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';

import { SettingsStore } from 'src/settings/core/settings.store';
import { Setting } from 'src/settings/entity/setting.entity';
import { TorrentsService } from 'src/torrents/torrents.service';

import { TrackersStore } from './core/trackers.store';
import { Tracker } from './entity/tracker.entity';
import { TrackerAdapterRegistry } from './tracker-adapter.registry';

@Injectable()
export class TrackerMaintenanceService {
  constructor(
    private readonly trackerAdapterRegistry: TrackerAdapterRegistry,
    private readonly trackersStore: TrackersStore,
    private readonly torrentsService: TorrentsService,
    private readonly settingsStore: SettingsStore,
  ) {}

  @Cron(CronExpression.EVERY_DAY_AT_4AM)
  async runTrackersCleanup(): Promise<void> {
    const [trackers, setting] = await Promise.all([
      this.trackersStore.find(),
      this.settingsStore.findOneOrThrow(),
    ]);

    await Promise.all(
      trackers.map((tracker) => {
        return this.runTrackerCleanup(tracker, setting);
      }),
    );
  }

  private async runTrackerCleanup(tracker: Tracker, setting: Setting) {
    const adapter = this.trackerAdapterRegistry.get(tracker.tracker);

    let enabledHitAndRun = setting.hitAndRun;

    if (tracker.hitAndRun !== null) {
      enabledHitAndRun = tracker.hitAndRun;
    }

    let notCompletedTorrentIds: string[] | undefined;

    if (enabledHitAndRun) {
      notCompletedTorrentIds = await adapter.seedRequirement();
    }

    let keepSeedSeconds =
      setting.keepSeedSeconds !== null ? setting.keepSeedSeconds : undefined;

    if (tracker.keepSeedSeconds !== null) {
      keepSeedSeconds = tracker.keepSeedSeconds;
    }

    if (notCompletedTorrentIds === undefined && keepSeedSeconds === undefined) {
      return;
    }

    await this.torrentsService.cleanupTrackerTorrents(
      tracker.tracker,
      keepSeedSeconds,
      notCompletedTorrentIds,
    );
  }
}
