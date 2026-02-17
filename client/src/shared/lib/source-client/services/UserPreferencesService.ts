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
export class UserPreferencesService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param userId
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public create(
        userId: string,
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/users/{userId}/preferences',
            path: {
                'userId': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param userId
     * @returns any
     * @throws ApiError
     */
    public find(
        userId: string,
    ): CancelablePromise<Array<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/users/{userId}/preferences',
            path: {
                'userId': userId,
            },
        });
    }
    /**
     * @param userId
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public reorder(
        userId: string,
        requestBody: ReorderPreferencesDto,
    ): CancelablePromise<Array<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)>> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/users/{userId}/preferences/reorder',
            path: {
                'userId': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param userId
     * @param preference
     * @returns any
     * @throws ApiError
     */
    public findOne(
        userId: string,
        preference: PreferenceEnum,
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/users/{userId}/preferences/{preference}',
            path: {
                'userId': userId,
                'preference': preference,
            },
        });
    }
    /**
     * @param userId
     * @param preference
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public update(
        userId: string,
        preference: PreferenceEnum,
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto),
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoQualityPreferenceDto | SourcePreferenceDto | AudioQualityPreferenceDto | AudioSpatialPreferenceDto)> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/users/{userId}/preferences/{preference}',
            path: {
                'userId': userId,
                'preference': preference,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param userId
     * @param preference
     * @returns any
     * @throws ApiError
     */
    public delete(
        userId: string,
        preference: 'tracker' | 'language' | 'resolution' | 'video-quality' | 'source' | 'audio-quality' | 'audio-spatial',
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/users/{userId}/preferences/{preference}',
            path: {
                'userId': userId,
                'preference': preference,
            },
        });
    }
}
