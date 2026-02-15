/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioPreferenceDto } from '../models/AudioPreferenceDto';
import type { LanguagePreferenceDto } from '../models/LanguagePreferenceDto';
import type { MeDto } from '../models/MeDto';
import type { PreferenceEnum } from '../models/PreferenceEnum';
import type { ResolutionPreferenceDto } from '../models/ResolutionPreferenceDto';
import type { SourcePreferenceDto } from '../models/SourcePreferenceDto';
import type { TrackerPreferenceDto } from '../models/TrackerPreferenceDto';
import type { UpdateMeDto } from '../models/UpdateMeDto';
import type { UserDto } from '../models/UserDto';
import type { VideoPreferenceDto } from '../models/VideoPreferenceDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MeService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns MeDto
     * @throws ApiError
     */
    public me(): CancelablePromise<MeDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/me',
        });
    }
    /**
     * @param requestBody
     * @returns UserDto
     * @throws ApiError
     */
    public updateMe(
        requestBody: UpdateMeDto,
    ): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param requestBody
     * @returns any
     * @throws ApiError
     */
    public createMePreference(
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoPreferenceDto | SourcePreferenceDto | AudioPreferenceDto),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/me/preferences',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns any
     * @throws ApiError
     */
    public mePreferences(): CancelablePromise<Array<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoPreferenceDto | SourcePreferenceDto | AudioPreferenceDto)>> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/me/preferences',
        });
    }
    /**
     * @param preference
     * @returns any
     * @throws ApiError
     */
    public mePreference(
        preference: PreferenceEnum,
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoPreferenceDto | SourcePreferenceDto | AudioPreferenceDto)> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/me/preferences/{preference}',
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
    public updateMePreference(
        preference: PreferenceEnum,
        requestBody: (TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoPreferenceDto | SourcePreferenceDto | AudioPreferenceDto),
    ): CancelablePromise<(TrackerPreferenceDto | LanguagePreferenceDto | ResolutionPreferenceDto | VideoPreferenceDto | SourcePreferenceDto | AudioPreferenceDto)> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/preferences/{preference}',
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
    public deleteMePreference(
        preference: 'tracker' | 'language' | 'resolution' | 'video-quality' | 'source' | 'audio-quality',
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/me/preferences/{preference}',
            path: {
                'preference': preference,
            },
        });
    }
    /**
     * @returns UserDto
     * @throws ApiError
     */
    public regenerateToken(): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/token/regenerate',
        });
    }
}
