/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SettingDto } from '../models/SettingDto';
import type { UpdateExternalSettingDto } from '../models/UpdateExternalSettingDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ExternalRelaySettingsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @param token
     * @param requestBody
     * @returns SettingDto
     * @throws ApiError
     */
    public update(
        token: string,
        requestBody: UpdateExternalSettingDto,
    ): CancelablePromise<SettingDto> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/{token}/external/relay/settings',
            path: {
                'token': token,
            },
            body: requestBody,
            mediaType: 'application/json',
        });
    }
}
