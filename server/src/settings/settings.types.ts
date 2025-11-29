export interface SettingToCreate {
  id: string;
  enebledlocalIp: boolean;
  downloadLimit: number;
  uploadLimit: number;
  hitAndRun: boolean;
  cacheRetention: string | null;
}

export interface SettingToUpdate {
  enebledlocalIp?: boolean;
  address?: string;
  downloadLimit?: number;
  uploadLimit?: number;
  hitAndRun?: boolean;
  cacheRetention?: string | null;
}
