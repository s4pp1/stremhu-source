/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type File = {
    info_hash: string;
    file_index: number;
    path: string;
    piece_length: number;
    size: number;
    offset: number;
    /**
     * A fájl már teljesen le van töltve, csak a stream-elni kell.
     */
    is_available: boolean;
};

