import {
  BadRequestException,
  HttpException,
  Inject,
  Injectable,
  Logger,
  ServiceUnavailableException,
  UnprocessableEntityException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AxiosInstance, AxiosResponse } from 'axios';
import { AxiosHeaders, isAxiosError } from 'axios';
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
  getTrackerStructureErrorMessage,
} from '../adapters.utils';
import { NCORE_LOGIN_PATH } from './ncore.constants';
import { NcoreLoginRequest } from './ncore.types';

@Injectable()
export class NcoreClientFactory {
  private readonly logger = new Logger(NcoreClientFactory.name);
  private readonly ncoreBaseUrl: string;

  private jar = new CookieJar();
  private axios: AxiosInstance = createAxios(this.jar);
  private loginInProgress: Promise<void> | null = null;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private trackerCredentialsService: TrackerCredentialsService,
  ) {
    this.ncoreBaseUrl =
      this.configService.getOrThrow<string>('tracker.ncore-url');

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload?: NcoreLoginRequest) {
    try {
      let credential: NcoreLoginRequest | undefined;

      if (payload) {
        credential = payload;
      } else {
        const response = await this.trackerCredentialsService.findOne(
          this.tracker,
        );

        if (!response) {
          throw new BadRequestException(
            getTrackerCredentialErrorMessage(this.tracker),
          );
        }

        credential = {
          username: response.username,
          password: response.password,
        };
      }

      const { username, password } = credential;

      await this.jar.removeAllCookies();
      const axios = createAxios(this.jar);

      const loginUrl = new URL(NCORE_LOGIN_PATH, this.ncoreBaseUrl);

      const form = new URLSearchParams();
      form.set('nev', username);
      form.set('pass', password);

      const response = await axios.post<string>(loginUrl.href, form, {
        responseType: 'text',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const isAuthError = this.isAuthError(response);
      if (isAuthError) {
        throw new UnprocessableEntityException(
          getTrackerLoginErrorMessage(this.tracker),
        );
      }
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }

      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new ServiceUnavailableException(errorMessage);
    }
  }

  private isAuthError(res: AxiosResponse) {
    const requestPath = _.get(res.request, ['path']) as string | undefined;
    const isLoginPath = requestPath?.includes(NCORE_LOGIN_PATH);

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
