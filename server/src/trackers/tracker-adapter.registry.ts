import { BadRequestException, Injectable } from '@nestjs/common';

import { BithumenAdapter } from './adapters/bithumen/bithumen.adapter';
import { FilelistAdapter } from './adapters/filelist/filelist.adapter';
import { InsaneAdapter } from './adapters/insane/insane.adapter';
import { MajomparadeAdapter } from './adapters/majomparade/majomparade.adapter';
import { NcoreAdapter } from './adapters/ncore/ncore.adapter';
import { TrackerEnum } from './enum/tracker.enum';
import { TrackerAdapter } from './tracker.types';

@Injectable()
export class TrackerAdapterRegistry {
  private readonly adapters: Map<TrackerEnum, TrackerAdapter>;

  constructor(
    ncore: NcoreAdapter,
    bithumen: BithumenAdapter,
    insane: InsaneAdapter,
    majomparade: MajomparadeAdapter,
    filelist: FilelistAdapter,
  ) {
    const entries: Array<[TrackerEnum, TrackerAdapter]> = [
      [ncore.tracker, ncore],
      [bithumen.tracker, bithumen],
      [insane.tracker, insane],
      [majomparade.tracker, majomparade],
      [filelist.tracker, filelist],
    ];
    this.adapters = new Map(entries);
  }

  get(tracker: TrackerEnum): TrackerAdapter {
    const adapter = this.adapters.get(tracker);
    if (!adapter) {
      throw new BadRequestException(`Nem regisztrált tracker: ${tracker}`);
    }
    return adapter;
  }

  list(): TrackerAdapter[] {
    return [...this.adapters.values()];
  }
}
