import type { AxiosRequestConfig } from 'axios';
import axios from 'axios';

import { RELAY_BASE_URL } from '../relay.constant';

export const RELAY_AXIOS_INSTANCE = axios.create({
  baseURL: RELAY_BASE_URL,
});

export const relayClientInstance = async <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const response = await RELAY_AXIOS_INSTANCE<T>({ ...config, ...options });
  return response.data;
};
