/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ManifestConfigDto = {
    /**
     * Konfigurációs kulcs
     */
    key: string;
    /**
     * Konfiguráció típusa
     */
    type: ManifestConfigDto.type;
    /**
     * Alapértelmezett érték
     */
    default?: string;
    /**
     * Megjelenített cím
     */
    title?: string;
    /**
     * Választható opciók
     */
    options?: Array<string>;
    /**
     * Kötelező-e a megadása
     */
    required?: string;
};
export namespace ManifestConfigDto {
    /**
     * Konfiguráció típusa
     */
    export enum type {
        TEXT = 'text',
        NUMBER = 'number',
        PASSWORD = 'password',
        CHECKBOX = 'checkbox',
        SELECT = 'select',
    }
}

