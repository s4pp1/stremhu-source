/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type TorrentState = {
    /**
     * checking_files=1, downloading_metadata=2, downloading=3, finished=4, seeding=5, unused_enum_for_backwards_compatibility_allocating=6, checking_resume_data=7 https://www.libtorrent.org/reference-Torrent_Status.html#torrent_status
     */
    state: number;
    progress: number;
};

