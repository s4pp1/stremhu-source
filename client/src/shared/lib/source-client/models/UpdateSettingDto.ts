/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type UpdateSettingDto = {
    /**
     * Local IP engedélyezése
     */
    enebledlocalIp?: boolean;
    /**
     * Cím
     */
    address?: string;
    /**
     * Hit and Run védelem
     */
    hitAndRun?: boolean;
    /**
     * Seedben tartás ideje (másodperc)
     */
    keepSeedSeconds?: number;
    /**
     * Cache megőrzési ideje (másodperc)
     */
    cacheRetentionSeconds?: number;
    /**
     * Katalógus token
     */
    catalogToken?: string | null;
};

