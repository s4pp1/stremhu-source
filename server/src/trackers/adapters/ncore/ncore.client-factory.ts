import {
  ForbiddenException,
  Inject,
  Injectable,
  Logger,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AxiosInstance, AxiosResponse } from 'axios';
import { AxiosError, AxiosHeaders } from 'axios';
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

  async login(payload: NcoreLoginRequest, firstLogin: boolean = false) {
    const { username, password } = payload;

    const axios = firstLogin ? createAxios(this.jar) : this.axios;

    const url = new URL(NCORE_LOGIN_PATH, this.ncoreBaseUrl).toString();

    const form = new URLSearchParams();
    form.set('nev', username);
    form.set('pass', password);

    const response = await axios.post(url, form, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    if (firstLogin) {
      const isAuthError = this.isAuthError(response);
      if (isAuthError) {
        throw new UnauthorizedException();
      }
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

        if (!isAuthError) {
          return res;
        }

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
