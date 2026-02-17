/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityPreferenceDto } from '../models/AudioQualityPreferenceDto';
import type { AudioSpatialPreferenceDto } from '../models/AudioSpatialPreferenceDto';
import type { LanguagePreferenceDto } from '../models/LanguagePreferenceDto';
import type { PreferenceEnum } from '../models/PreferenceEnum';
import type { ReorderPreferencesDto } from '../models/ReorderPreferencesDto';
import type { ResolutionPreferenceDto } from '../models/ResolutionPreferenceDto';
import type { SourcePreferenceDto } from '../models/SourcePreferenceDto';
import type { TrackerPreferenceDto } from '../models/TrackerPreferenceDto';
import type { VideoQualityPreferenceDto } from '../models/VideoQualityPreferenceDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MePreferencesService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public create(
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/me/preference',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns any
     * @throws ApiError
     */
    public find(): CancelablePromise<Array<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/me/preference',
        });
    }
    /**
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public reorder(
        requestBody: ReorderPreferencesDto,
    ): CancelablePromise<Array<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)>> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/me/preference/reorder',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param preference
     * @returns any
     * @throws ApiError
     */
    public findOne(
        preference: PreferenceEnum,
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/me/preference/{preference}',
            path: {
                'preference': preference,
            },
        });
    }
    /**
     * @param preference
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public update(
        preference: PreferenceEnum,
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto),
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/preference/{preference}',
            path: {
                'preference': preference,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param preference
     * @returns any
     * @throws ApiError
     */
    public delete(
        preference: 'tracker' | 'language' | 'resolution' | 'video-quality' | 'source' | 'audio-quality' | 'audio-spatial',
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/me/preference/{preference}',
            path: {
                'preference': preference,
            },
        });
    }
}
