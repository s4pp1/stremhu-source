import {
  ForbiddenException,
  Inject,
  Injectable,
  Logger,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AxiosInstance } from 'axios';
import { AxiosError, AxiosHeaders } from 'axios';
import { load } from 'cheerio';
import _ from 'lodash';
import { CookieJar } from 'tough-cookie';

import { createAxios } from 'src/trackers/common/create-axios';
import { TrackerCredentialsService } from 'src/trackers/credentials/tracker-credentials.service';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';

import { TRACKER_TOKEN } from '../adapters.types';
import {
  getTrackerCredentialErrorMessage,
  getTrackerLoginErrorMessage,
  getTrackerRefreshMessage,
} from '../adapters.utils';
import { BITHUMEN_LOGIN_PATH } from './bithumen.constants';
import { BithumenLoginRequest } from './bithumen.types';

@Injectable()
export class BithumenClientFactory {
  private readonly logger = new Logger(BithumenClientFactory.name);
  private readonly bithumenBaseUrl: string;

  private jar = new CookieJar();
  private axios: AxiosInstance = createAxios(this.jar);
  private loginInProgress: Promise<void> | null = null;

  userId: string = '';

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private trackerCredentialsService: TrackerCredentialsService,
  ) {
    this.bithumenBaseUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload: BithumenLoginRequest, firstLogin: boolean = false) {
    const { username, password } = payload;

    const axios = firstLogin ? createAxios(this.jar) : this.axios;

    const url = new URL(BITHUMEN_LOGIN_PATH, this.bithumenBaseUrl).toString();

    const form = new URLSearchParams();
    form.set('username', username);
    form.set('password', password);
    form.set('returnto', '/');

    const response = await axios.post(url, form, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    if (typeof response.data !== 'string') {
      throw new UnauthorizedException();
    }

    const $ = load(response.data);
    const userDetailPath = $('#status a[href*="/userdetails.php?"]')
      .first()
      .attr('href');

    if (!userDetailPath) {
      throw new UnauthorizedException();
    }

    const userDetailUrl = new URL(userDetailPath, this.bithumenBaseUrl);
    const userId = userDetailUrl.searchParams.get('id') || '';
    this.userId = userId;
  }

  private initInterceptors() {
    this.axios.interceptors.response.use(
      async (res) => {
        const requestPath = _.get(res.request, ['path']) as string | undefined;
        const checkPaths = ['/login.php', BITHUMEN_LOGIN_PATH];

        const isLoginPath = checkPaths.some((checkPath) =>
          requestPath?.includes(checkPath),
        );

        if (isLoginPath) {
          if (res.config._retry) {
            throw new ForbiddenException(
              getTrackerLoginErrorMessage(this.tracker),
            );
          }

          await this.relogin();

          if (res.config.headers) {
            const headers = AxiosHeaders.from(res.config.headers);
            headers.delete('cookie');
            res.config.headers = headers;
          }

          res.config._retry = true;

          return this.axios.request(res.config);
        }

        return res;
      },
      async (error: AxiosError) => {
        const { response, config } = error;

        const sessionExpired =
          response?.status === 401 || response?.status === 403;

        if (!sessionExpired || !config || config._retry) {
          return Promise.reject(error);
        }

        await this.relogin();

        config._retry = true;

        return this.axios.request(config);
      },
    );
  }

  private async relogin() {
    if (this.loginInProgress) {
      return this.loginInProgress;
    }

    this.loginInProgress = this.doRelogin();

    try {
      await this.loginInProgress;
    } finally {
      this.loginInProgress = null;
    }

    return this.loginInProgress;
  }

  private async doRelogin() {
    this.logger.log(getTrackerRefreshMessage(this.tracker));

    const credential = await this.trackerCredentialsService.findOne(
      this.tracker,
    );

    if (!credential) {
      throw new ForbiddenException(
        getTrackerCredentialErrorMessage(this.tracker),
      );
    }

    await this.login(credential);
  }
}
