/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type UpdateRelaySettingsDto = {
    /**
     * Port azonosító
     */
    port?: number;
    /**
     * Letöltési korlát
     */
    downloadLimit?: number;
    /**
     * Feltöltési korlát
     */
    uploadLimit?: number;
    /**
     * Kapcsolatok korlátja
     */
    connectionsLimit?: number;
    /**
     * Torrentenkénti kapcsolatok korlátja
     */
    torrentConnectionsLimit?: number;
    /**
     * UPnP és NAT-PMP engedélyezése
     */
    enableUpnpAndNatpmp?: boolean;
};

