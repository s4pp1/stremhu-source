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
import type { AxiosInstance } from 'axios';
import { AxiosHeaders, isAxiosError } from 'axios';
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
  getTrackerStructureErrorMessage,
} from '../adapters.utils';
import { MAJOMPARADE_LOGIN_PATH } from './majomparade.constants';
import { MajomparadeLoginRequest } from './majomparade.types';

@Injectable()
export class MajomparadeClientFactory {
  private readonly logger = new Logger(MajomparadeClientFactory.name);
  private readonly majomparadeBaseUrl: string;

  private jar = new CookieJar();
  private axios: AxiosInstance = createAxios(this.jar);
  private loginInProgress: Promise<void> | null = null;

  constructor(
    @Inject(TRACKER_TOKEN) private readonly tracker: TrackerEnum,
    private configService: ConfigService,
    private trackerCredentialsService: TrackerCredentialsService,
  ) {
    this.majomparadeBaseUrl = this.configService.getOrThrow<string>(
      'tracker.majomparade-url',
    );

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload?: MajomparadeLoginRequest) {
    try {
      let credential: MajomparadeLoginRequest | undefined;

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

      const loginUrl = new URL(MAJOMPARADE_LOGIN_PATH, this.majomparadeBaseUrl);

      const loginResponse = await axios.get<string>(loginUrl.href, {
        responseType: 'text',
      });

      const $login = load(loginResponse.data);
      const getUnique = $login('.rejtett_input[name="getUnique"]')
        .first()
        .attr('value');

      if (!getUnique) {
        throw new Error('getUnique nem található');
      }

      const form = new URLSearchParams();
      form.set('nev', username);
      form.set('jelszo', password);
      form.set('getUnique', getUnique);

      const response = await axios.post(`${loginUrl.href}?belepes`, form, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (response.data !== 'location="index.php";') {
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

  private initInterceptors() {
    this.axios.interceptors.response.use(
      async (res) => {
        const requestPath = _.get(res.request, ['path']) as string | undefined;
        const isLoginPath = requestPath?.includes(MAJOMPARADE_LOGIN_PATH);

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
