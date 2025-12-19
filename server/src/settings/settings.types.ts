export interface SettingToCreate {
  id: string;
  enebledlocalIp: boolean;
  downloadLimit: number;
  uploadLimit: number;
  hitAndRun: boolean;
  cacheRetentionSeconds: number | null;
}

export interface SettingToUpdate {
  enebledlocalIp?: boolean;
  address?: string;
  downloadLimit?: number;
  uploadLimit?: number;
  hitAndRun?: boolean;
  cacheRetentionSeconds?: number | null;
  catalogToken?: string | null;
}
