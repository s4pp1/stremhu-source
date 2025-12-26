import rangeParser from 'range-parser';

import { RangeErrorEnum } from '../enum/range-error.enum';
import { CalculateRange } from '../type/calculate-range.type';
import { CalculatedRange } from '../type/calculated-range.type';

export function calculateRange(payload: CalculateRange): CalculatedRange {
  const { rangeHeader, total } = payload;

  if (!rangeHeader) {
    return {
      start: 0,
      end: total - 1,
      contentLength: total,
    };
  }

  const parsedRange = rangeParser(total, rangeHeader);

  if (parsedRange === -1) return RangeErrorEnum.RANGE_NOT_SATISFIABLE;
  if (parsedRange === -2) return RangeErrorEnum.RANGE_MALFORMED;

  const [range] = parsedRange;

  return {
    start: range.start,
    end: range.end,
    contentLength: range.end - range.start + 1,
  };
}
