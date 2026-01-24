/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type File = {
    infoHash: string;
    fileIndex: number;
    path: string;
    pieceLength: number;
    size: number;
    offset: number;
    /**
     * A fájl már teljesen le van töltve, csak a stream-elni kell.
     */
    isAvailable: boolean;
};

