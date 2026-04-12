import type { AxiosRequestConfig } from 'axios';
import axios from 'axios';

export const CATALOG_AXIOS_INSTANCE = axios.create({
  withCredentials: true,
});

export const catalogClientInstance = async <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const response = await CATALOG_AXIOS_INSTANCE<T>({ ...config, ...options });
  return response.data;
};
