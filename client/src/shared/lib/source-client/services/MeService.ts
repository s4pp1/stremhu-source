/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MeDto } from '../models/MeDto';
import type { UpdateMeDto } from '../models/UpdateMeDto';
import type { UserDto } from '../models/UserDto';
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
