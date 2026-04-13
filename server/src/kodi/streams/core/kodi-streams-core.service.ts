import { Injectable } from '@nestjs/common';
import { first } from 'lodash';

import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { ParsedStreamSeries } from 'src/stremio/streams/type/parsed-stream-series.type';
import { TorrentVideosService } from 'src/torrent-videos/torrent-videos.service';
import { TorrentVideo } from 'src/torrent-videos/type/torrent-video.type';
import { User } from 'src/users/entity/user.entity';

import { FindKodiImdbStreamsDto } from '../dto/find-kodi-imdb-streams.dto';
import { KodiImdbStreamDto } from '../dto/kodi-imdb-stream.dto';
import { KodiImdbStreamsDto } from '../dto/kodi-imdb-streams.dto';

@Injectable()
export class KodiStreamsCoreService {
  constructor(private readonly torrentVideosService: TorrentVideosService) {}

  async imdbStreams(
    user: User,
    imdbId: string,
    payload?: FindKodiImdbStreamsDto,
  ): Promise<KodiImdbStreamsDto> {
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

    let streams: KodiImdbStreamDto[] = torrentVideos.map((torrentVideo) =>
      this.imdbStream(torrentVideo),
    );

    if (user.onlyBestTorrent) {
      const bestStream = first(streams);
      streams = bestStream ? [bestStream] : [];
    }

    return {
      streams,
      errors: trackerErrors,
    };
  }

  private imdbStream(torrentVideo: TorrentVideo): KodiImdbStreamDto {
    return {
      tracker: torrentVideo.tracker,
      torrentName: torrentVideo.torrentName,
      fileName: torrentVideo.fileName,
      seeders: torrentVideo.seeders,
      size: torrentVideo.fileSize,
      languages: [torrentVideo.language],
      resolution: torrentVideo.resolution,
      videoQualities: torrentVideo['video-quality'],
      audioQuality: torrentVideo['audio-quality'],
      audioSpatial: torrentVideo['audio-spatial'],
      source: torrentVideo.source,
      url: torrentVideo.playUrl,
    };
  }
}
