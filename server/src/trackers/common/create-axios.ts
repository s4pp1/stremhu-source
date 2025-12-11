import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { HttpCookieAgent, HttpsCookieAgent } from 'http-cookie-agent/http';
import type { CookieJar } from 'tough-cookie';

export function createAxios(jar: CookieJar): AxiosInstance {
  return axios.create({
    jar,
    httpAgent: new HttpCookieAgent({
      cookies: { jar },
      keepAlive: true,
      family: 4,
    }),
    httpsAgent: new HttpsCookieAgent({
      cookies: { jar },
      keepAlive: true,
      family: 4,
    }),
    withCredentials: true,
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
      Accept:
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    },
    timeout: 20_000,
    validateStatus: (status) => status >= 200 && status < 400,
  });
}
