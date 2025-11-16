/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangePasswordDto } from '../models/ChangePasswordDto';
import type { ChangeUsernameDto } from '../models/ChangeUsernameDto';
import type { MeUserDto } from '../models/MeUserDto';
import type { UpdateMePreferencesDto } from '../models/UpdateMePreferencesDto';
import type { UserDto } from '../models/UserDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MeService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns MeUserDto
     * @throws ApiError
     */
    public usersMeControllerMe(): CancelablePromise<MeUserDto> {
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
    public usersMeControllerUpdateMe(
        requestBody: UpdateMePreferencesDto,
    ): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/preferences',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param requestBody
     * @returns UserDto
     * @throws ApiError
     */
    public usersMeControllerChangeUsername(
        requestBody: ChangeUsernameDto,
    ): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/username',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param requestBody
     * @returns UserDto
     * @throws ApiError
     */
    public usersMeControllerChangePassword(
        requestBody: ChangePasswordDto,
    ): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/password',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @returns UserDto
     * @throws ApiError
     */
    public usersMeControllerChangeStremioToken(): CancelablePromise<UserDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/me/stremio-token',
        });
    }
}
