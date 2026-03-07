import {
  BadRequestException,
  HttpException,
  Inject,
  Injectable,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AxiosInstance } from 'axios';
import { AxiosHeaders, isAxiosError } from 'axios';
import { get } from 'lodash';
import { CookieJar } from 'tough-cookie';

import { createAxios } from 'src/trackers/common/create-axios';
import { TrackersStore } from 'src/trackers/core/trackers.store';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

import { AdapterLoginRequest, TRACKER_TOKEN } from '../adapters.types';
import {
  getTrackerCredentialErrorMessage,
  getTrackerLoginErrorMessage,
  getTrackerRefreshMessage,
} from '../adapters.utils';
import { LOGIN_PATH } from './majomparade.constants';
import { MajomparadeLoginResponse } from './majomparade.types';

@Injectable()
export class MajomparadeClientFactory {
  private readonly logger = new Logger(MajomparadeClientFactory.name);
  private readonly baseUrl: string;

  private jar = new CookieJar();
  private axios: AxiosInstance = createAxios(this.jar);
  private loginInProgress: Promise<void> | null = null;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private trackersStore: TrackersStore,
  ) {
    this.baseUrl = this.configService.getOrThrow<string>(
      'tracker.majomparade-url',
    );

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload?: AdapterLoginRequest) {
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

    const response = await axios.post<MajomparadeLoginResponse>(
      `${loginUrl.href}`,
      form,
      {
        responseType: 'json',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      },
    );

    if (!response.data.success) {
      throw new Error(getTrackerLoginErrorMessage(this.tracker));
    }
  }

  private initInterceptors() {
    this.axios.interceptors.response.use(
      async (res) => {
        const requestPath = get(res.request, ['path']) as string | undefined;
        const isLoginPath = requestPath?.includes('/login/');

        if (isLoginPath) {
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

  private async relogin(): Promise<void> {
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
