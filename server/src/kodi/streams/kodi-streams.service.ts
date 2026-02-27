import { Injectable } from '@nestjs/common';

import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';
import { TorrentVideosService } from 'src/torrent-videos/torrent-videos.service';
import { TorrentVideo } from 'src/torrent-videos/type/torrent-video.type';
import { User } from 'src/users/entity/user.entity';

import { FindKodiImdbStreamsDto } from './dto/find-kodi-imdb-streams.dto';

@Injectable()
export class KodiStreamsService {
  constructor(private readonly torrentVideosService: TorrentVideosService) {}

  async imdbStreams(
    user: User,
    imdbId: string,
    payload?: FindKodiImdbStreamsDto,
  ): Promise<TorrentVideo[]> {
    let mediaType = MediaTypeEnum.MOVIE;

    let series: ParsedStreamSeries | undefined;

    if (payload?.season && payload?.episode) {
      mediaType = MediaTypeEnum.SERIES;
      series = {
        season: payload.season,
        episode: payload.episode,
      };
    }

    const [torrentVideos, trackerErrors] =
      await this.torrentVideosService.findByImdb({
        user,
        imdbId,
        mediaType,
        series,
      });

    return torrentVideos;
  }
}
