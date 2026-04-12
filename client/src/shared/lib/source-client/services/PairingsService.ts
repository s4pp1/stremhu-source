/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PairInitDto } from '../models/PairInitDto';
import type { PairStatusDto } from '../models/PairStatusDto';
import type { PairStatusRequestDto } from '../models/PairStatusRequestDto';
import type { PairVerifyDto } from '../models/PairVerifyDto';
import type { PairVerifyRequestDto } from '../models/PairVerifyRequestDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class PairingsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * @returns PairInitDto
     * @throws ApiError
     */
    public init(): CancelablePromise<PairInitDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/auth/pair/init',
        });
    }
    /**
     * @param requestBody
     * @returns PairStatusDto
     * @throws ApiError
     */
    public status(
        requestBody: PairStatusRequestDto,
    ): CancelablePromise<PairStatusDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/auth/pair/status',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
    /**
     * @param requestBody
     * @returns PairVerifyDto
     * @throws ApiError
     */
    public verify(
        requestBody: PairVerifyRequestDto,
    ): CancelablePromise<PairVerifyDto> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/auth/pair/verify',
            body: requestBody,
            mediaType: 'application/json',
        });
    }
}
