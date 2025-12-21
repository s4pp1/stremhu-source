export interface SettingToCreate {
  id: string;
  enebledlocalIp: boolean;
  downloadLimit: number;
  uploadLimit: number;
  hitAndRun: boolean;
  keepSeedSeconds: number | null;
  cacheRetentionSeconds: number | null;
}

export interface SettingToUpdate {
  enebledlocalIp?: boolean;
  address?: string;
  downloadLimit?: number;
  uploadLimit?: number;
  hitAndRun?: boolean;
  keepSeedSeconds?: number | null;
  cacheRetentionSeconds?: number | null;
  catalogToken?: string | null;
}
