/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateSetupDto } from '../models/CreateSetupDto';
import type { LocalUrlDto } from '../models/LocalUrlDto';
import type { LocalUrlRequestDto } from '../models/LocalUrlRequestDto';
import type { SettingDto } from '../models/SettingDto';
import type { StatusDto } from '../models/StatusDto';
import type { UpdateSettingDto } from '../models/UpdateSettingDto';
import type { UserDto } from '../models/UserDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class SettingsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns SettingDto
     * @throws ApiError
     */
    public findOne(): CancelablePromise<SettingDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/settings',
        });
    }
    /**
     * @param requestBody
     * @returns SettingDto
     * @throws ApiError
     */
    public update(
        requestBody: UpdateSettingDto,
    ): CancelablePromise<SettingDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/settings',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param requestBody
     * @returns LocalUrlDto
     * @throws ApiError
     */
    public buildLocalUrl(
        requestBody: LocalUrlRequestDto,
    ): CancelablePromise<LocalUrlDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/settings/local-url',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns any
     * @throws ApiError
     */
    public cacheTorrentsCleanup(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/settings/cache/torrents/retention-cleanup',
        });
    }
    /**
     * @param requestBody
     * @returns UserDto
     * @throws ApiError
     */
    public create(
        requestBody: CreateSetupDto,
    ): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/settings/setup',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns StatusDto
     * @throws ApiError
     */
    public status(): CancelablePromise<StatusDto> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/settings/setup/status',
        });
    }
}
