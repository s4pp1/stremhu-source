/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type PairInitDto = {
    /**
     * A 4 jegyű kód, amit a felhasználónak be kell gépelnie
     */
    userCode: string;
    /**
     * Az eszköz egyedi azonosítója a státusz lekérdezéséhez
     */
    deviceCode: string;
    /**
     * A kód lejárati ideje
     */
    expiresAt: string;
};

