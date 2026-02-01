import {
  BadRequestException,
  HttpException,
  Inject,
  Injectable,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AxiosInstance, AxiosResponse } from 'axios';
import { AxiosHeaders, isAxiosError } from 'axios';
import { load } from 'cheerio';
import _ from 'lodash';
import { CookieJar } from 'tough-cookie';

import { createAxios } from 'src/trackers/common/create-axios';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { AdapterLoginRequest, TRACKER_TOKEN } from '../adapters.types';
import {
  getTrackerCredentialErrorMessage,
  getTrackerLoginErrorMessage,
  getTrackerRefreshMessage,
  getTrackerStructureErrorMessage,
} from '../adapters.utils';
import { INDEX_PATH, LOGIN_PATH } from './bithumen.constants';

@Injectable()
export class BithumenClientFactory {
  private readonly logger = new Logger(BithumenClientFactory.name);
  private readonly baseUrl: string;

  private jar = new CookieJar();
  private axios: AxiosInstance = createAxios(this.jar);
  private loginInProgress: Promise<void> | null = null;

  private userId: string | undefined;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private trackersStore: TrackersStore,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>(
      'tracker.bithumen-url',
    );

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload?: AdapterLoginRequest) {
    try {
      let credential = payload;

      if (!credential) {
        const tracker = await this.trackersStore.findOneByTracker(this.tracker);

        if (!tracker) {
          throw new BadRequestException(
            getTrackerCredentialErrorMessage(this.tracker),
          );
        }

        credential = {
          username: tracker.username,
          password: tracker.password,
        };
      }

      const { username, password } = credential;

      await this.jar.removeAllCookies();
      const axios = createAxios(this.jar);

      const loginUrl = new URL(LOGIN_PATH, this.baseUrl);

      const form = new URLSearchParams();
      form.set('username', username);
      form.set('password', password);
      form.set('returnto', '/');

      const response = await axios.post<string>(loginUrl.href, form, {
        responseType: 'text',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const isAuthError = this.isAuthError(response);
      if (isAuthError) {
        throw new Error(getTrackerLoginErrorMessage(this.tracker));
      }
    } catch (error) {
      if (isAxiosError(error) && error.status === 401) {
        throw new Error(getTrackerLoginErrorMessage(this.tracker));
      }

      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  async getUserId(): Promise<string> {
    try {
      if (this.userId) return this.userId;

      const indexUrl = new URL(INDEX_PATH, this.baseUrl);
      const response = await this.client.get<string>(indexUrl.href, {
        responseType: 'text',
      });

      const $ = load(response.data);
      const userDetailPath = $('#status a[href*="/userdetails.php?"]')
        .first()
        .attr('href');

      if (!userDetailPath) {
        throw new Error(`"userDetailPath": ${userDetailPath} nem található`);
      }

      const userDetailUrl = new URL(userDetailPath, this.baseUrl);
      const userId = userDetailUrl.searchParams.get('id');

      if (!userId) {
        throw new Error(`"userId": ${userId} nem található`);
      }

      this.userId = userId;

      return userId;
    } catch (error) {
      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage);
    }
  }

  private isAuthError(res: AxiosResponse) {
    const requestPath = _.get(res.request, ['path']) as string | undefined;
    const checkPaths = ['/login.php', LOGIN_PATH];

    const isLoginPath = checkPaths.some((checkPath) =>
      requestPath?.includes(checkPath),
    );

    return isLoginPath;
  }

  private initInterceptors() {
    this.axios.interceptors.response.use(
      async (res) => {
        const isAuthError = this.isAuthError(res);

        if (isAuthError) {
          await this.relogin();

          if (res.config.headers) {
            const headers = AxiosHeaders.from(res.config.headers);
            headers.delete('cookie');
            res.config.headers = headers;
          }

          return this.axios.request(res.config);
        }

        return res;
      },
      async (error) => {
        if (error instanceof HttpException) {
          throw error;
        }

        if (isAxiosError(error)) {
          const authErrorStatus = [401, 403];

          const isAuthError = error.status
            ? authErrorStatus.includes(error.status)
            : false;

          const { config } = error;

          if (!isAuthError || !config) {
            throw error;
          }

          await this.relogin();

          if (config.headers) {
            const headers = AxiosHeaders.from(config.headers);
            headers.delete('cookie');
            config.headers = headers;
          }

          return this.axios.request(config);
        }

        throw error;
      },
    );
  }

  private async relogin() {
    if (this.loginInProgress) {
      return this.loginInProgress;
    }

    this.loginInProgress = this.login();

    try {
      this.logger.log(getTrackerRefreshMessage(this.tracker));
      await this.loginInProgress;
    } finally {
      this.loginInProgress = null;
    }
  }
}
