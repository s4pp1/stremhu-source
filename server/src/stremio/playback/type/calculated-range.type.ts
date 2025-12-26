import { RangeErrorEnum } from '../enum/range-error.enum';

export type CalculatedRangeDetails = {
  start: number;
  end: number;
  contentLength: number;
};

export type CalculatedRange = CalculatedRangeDetails | RangeErrorEnum;
