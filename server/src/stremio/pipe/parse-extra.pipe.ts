import { Injectable, PipeTransform } from '@nestjs/common';

import type { ParsedExtra } from '../type/parsed-extra.type';

@Injectable()
export class ParseExtraPipe implements PipeTransform<string, ParsedExtra> {
  transform(value: string | undefined): ParsedExtra {
    let search: string | undefined;
    let genre: string | undefined;
    let skip: number | undefined;

    if (!value) {
      return { search, genre, skip };
    }

    const parts = value.split('&');

    parts.forEach((part) => {
      const [key, value] = part.split('=');

      if (key === 'skip') {
        skip = Number(value);
      }

      if (key === 'search') {
        search = value;
      }

      if (key === 'genre') {
        genre = value;
      }
    });

    return { search, genre, skip };
  }
}
