/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ManifestExtraDto = {
    /**
     * Extra paraméter neve
     */
    name: ManifestExtraDto.name;
    /**
     * Kötelező-e a paraméter
     */
    isRequired?: boolean;
    /**
     * Választható opciók
     */
    options?: Array<string>;
    /**
     * Maximálisan választható opciók száma
     */
    optionsLimit?: number;
};
export namespace ManifestExtraDto {
    /**
     * Extra paraméter neve
     */
    export enum name {
        SEARCH = 'search',
        GENRE = 'genre',
        SKIP = 'skip',
    }
}

