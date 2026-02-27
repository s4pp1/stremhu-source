import { Injectable } from '@nestjs/common';
import { compact } from 'lodash';

import { MediaTypeEnum } from 'src/common/enum/media-type.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { TorrentVideosService } from 'src/torrent-videos/torrent-videos.service';
import { TorrentVideo } from 'src/torrent-videos/type/torrent-video.type';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { User } from 'src/users/entity/user.entity';

import { VideoQualityEnum } from '../../preference-items/enum/video-quality.enum';
import { StreamDto } from './dto/stremio-stream.dto';
import { StreamIdTypeEnum } from './enum/stream-id-type.enum';
import { ParsedStreamId } from './type/parsed-stream-id.type';
import { ParsedStreamSeries } from './type/parsed-stream-series.type';

@Injectable()
export class StremioStreamsService {
  constructor(private readonly torrentVideosService: TorrentVideosService) {}

  async streams(
    user: User,
    mediaType: MediaTypeEnum,
    payload: ParsedStreamId,
  ): Promise<StreamDto[]> {
    const { type } = payload;

    switch (type) {
      case StreamIdTypeEnum.IMDB:
        return this.imdbStreams(
          user,
          mediaType,
          payload.imdbId,
          payload.series,
        );
      case StreamIdTypeEnum.TORRENT:
        return this.torrentStreams(user, payload.tracker, payload.torrentId);
    }
  }

  private async imdbStreams(
    user: User,
    mediaType: MediaTypeEnum,
    imdbId: string,
    series?: ParsedStreamSeries,
  ): Promise<StreamDto[]> {
    const [torrentVideos, trackerErrors] =
      await this.torrentVideosService.findByImdb({
        user,
        imdbId,
        mediaType,
        series,
      });

    const streams: StreamDto[] = torrentVideos.map((torrentVideo) =>
      this.imdbStream(torrentVideo),
    );
    const streamErrors: StreamDto[] = trackerErrors.map((trackerError) =>
      this.streamError(trackerError),
    );

    return [...streams, ...streamErrors];
  }

  private imdbStream(torrentVideo: TorrentVideo): StreamDto {
    const videoQualities = torrentVideo['video-quality'].filter(
      (videoQuality) => videoQuality.value !== VideoQualityEnum.SDR,
    );

    const readableVideoQualities = videoQualities
      .map((videoQuality) => videoQuality.label)
      .join(', ');

    const nameArray = compact([
      torrentVideo.resolution.label,
      readableVideoQualities,
    ]);

    const isCamSource = torrentVideo.source.value === SourceEnum.THEATRICAL;

    if (isCamSource) {
      nameArray.push('📹 CAM');
    }

    if (torrentVideo.isInRelay) {
      nameArray.unshift('⭐');
    }

    const readableLanguage = `🌍 ${torrentVideo.language.label}`;

    const fileSize = `💾 ${torrentVideo.fileSize}`;
    const seeders = `👥 ${torrentVideo.seeders}`;
    const tracker = `🧲 ${torrentVideo.tracker.label}`;

    let audioQuality: string | undefined;

    if (torrentVideo['audio-quality']) {
      audioQuality = `🔈 ${torrentVideo['audio-quality'].label}`;
    }

    const readableAudioSpatial = torrentVideo['audio-spatial']?.label;

    const descriptionArray = compact([
      compact([tracker, seeders, fileSize]).join(' | '),
      compact([readableLanguage, audioQuality, readableAudioSpatial]).join(
        ' | ',
      ),
    ]);

    const bingeGroup = [
      torrentVideo.tracker.value,
      torrentVideo.torrentId,
    ].join('-');

    return {
      name: nameArray.join(' | '),
      description: descriptionArray.join('\n'),
      url: torrentVideo.playUrl,
      behaviorHints: {
        notWebReady: true,
        bingeGroup,
        filename: torrentVideo.fileName,
      },
    };
  }

  private streamError(message: string) {
    return {
      name: '❗ HIBA ❗',
      description: `❗ ${message} ❗`,
      url: 'http://hiba.tortent',
      behaviorHints: {
        notWebReady: false,
      },
    };
  }

  private async torrentStreams(
    user: User,
    tracker: TrackerEnum,
    torrentId: string,
  ): Promise<StreamDto[]> {
    const baseTorrentVideos = await this.torrentVideosService.findByTorrentId(
      user,
      tracker,
      torrentId,
    );

    return baseTorrentVideos.map((torrentVideo) => ({
      name: `💾 ${torrentVideo.fileSize}`,
      behaviorHints: {
        notWebReady: true,
      },
      description: torrentVideo.fileName,
      url: torrentVideo.playUrl,
    }));
  }
}
