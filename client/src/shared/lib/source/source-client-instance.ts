import type { AxiosRequestConfig } from 'axios'
import axios from 'axios'

export const AXIOS_INSTANCE = axios.create({
  withCredentials: true,
})

export const sourceClientInstance = async <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const response = await AXIOS_INSTANCE<T>({ ...config, ...options })
  return response.data
}
