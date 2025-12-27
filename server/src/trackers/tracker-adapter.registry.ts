import { BadRequestException, Injectable } from '@nestjs/common';

import { BithumenAdapter } from './adapters/bithumen/bithumen.adapter';
import { DiabloAdapter } from './adapters/diablo/diablo.adapter';
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
    majomparade: MajomparadeAdapter,
    diablo: DiabloAdapter,
  ) {
    const entries: Array<[TrackerEnum, TrackerAdapter]> = [
      [ncore.tracker, ncore],
      [bithumen.tracker, bithumen],
      [majomparade.tracker, majomparade],
      [diablo.tracker, diablo],
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
