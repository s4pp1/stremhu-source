/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type PairStatusDto = {
    /**
     * A párosítás állapota (pending, linked, expired)
     */
    status: PairStatusDto.status;
    /**
     * A felhasználó API tokenje (csak 'linked' állapot esetén)
     */
    token?: string;
};
export namespace PairStatusDto {
    /**
     * A párosítás állapota (pending, linked, expired)
     */
    export enum status {
        PENDING = 'pending',
        LINKED = 'linked',
        EXPIRED = 'expired',
    }
}

