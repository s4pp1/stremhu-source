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
  getTrackerStructureErrorMessage,
} from '../adapters.utils';
import { LOGIN_PAGE_PATH, LOGIN_PATH } from './filelist.constants';

@Injectable()
export class FilelistClientFactory {
  private readonly logger = new Logger(FilelistClientFactory.name);
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
      'tracker.filelist-url',
    );

    this.initInterceptors();
  }

  get client(): AxiosInstance {
    return this.axios;
  }

  async login(payload?: AdapterLoginRequest): Promise<void> {
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

      const loginPageUrl = new URL(LOGIN_PAGE_PATH, this.baseUrl);
      loginPageUrl.searchParams.set('returnto', '/');

      const loginPageResponse = await axios.get<string>(loginPageUrl.href, {
        responseType: 'text',
      });

      const form = this.buildLoginForm(loginPageResponse.data);
      form.set('username', username);
      form.set('password', password);

      const loginUrl = new URL(LOGIN_PATH, this.baseUrl);

      const response = await axios.post<string>(loginUrl.href, form, {
        responseType: 'text',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (this.isAuthError(response)) {
        throw new Error(getTrackerLoginErrorMessage(this.tracker));
      }

      this.axios = axios;
      this.initInterceptors();
    } catch (error) {
      if (error instanceof BadRequestException) {
        throw error;
      }

      if (error instanceof Error && error.message.includes('Sikertelen')) {
        throw error;
      }

      const errorMessage = getTrackerStructureErrorMessage(this.tracker);
      this.logger.error(errorMessage, error);
      throw new Error(errorMessage, { cause: error });
    }
  }

  private buildLoginForm(html: string): URLSearchParams {
    const $ = load(html);
    const form = new URLSearchParams();

    $('form input[name]').each((_, element) => {
      const name = $(element).attr('name');
      const value = $(element).attr('value') ?? '';

      if (name) {
        form.set(name, value);
      }
    });

    if (!form.has('validator')) {
      throw new Error('A Filelist login validator nem talalhato.');
    }

    return form;
  }

  private isAuthError(res: AxiosResponse): boolean {
    const requestPath = get(res.request, ['path']) as string | undefined;
    const isLoginPath =
      requestPath?.includes(LOGIN_PAGE_PATH) ||
      requestPath?.includes(LOGIN_PATH);

    if (!isLoginPath) {
      return false;
    }

    const html = typeof res.data === 'string' ? res.data : '';
    const normalizedHtml = html
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();

    return (
      html.includes('name="username"') ||
      html.includes("name='username'") ||
      normalizedHtml.includes('login on any ip') ||
      normalizedHtml.includes('numarul maxim permis de actiuni')
    );
  }

  private initInterceptors(): void {
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
