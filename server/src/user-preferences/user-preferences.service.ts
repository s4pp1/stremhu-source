import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { isUndefined, omitBy } from 'lodash';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';

import { UserPreferencesStore } from './core/user-preferences.store';
import { UserPreference as UserPreferenceEntity } from './entity/user-preference.entity';
import { userPreferenceSchema } from './schema';
import { UserPreferenceToCreate } from './type/user-preference-to-create.type';
import { UserPreferenceToUpdate } from './type/user-preference-to-update.type';
import { UserPreference } from './type/user-preference.type';

@Injectable()
export class UserPreferencesService {
  private readonly logger = new Logger(UserPreferencesService.name);

  constructor(private readonly userPreferencesStore: UserPreferencesStore) {}

  async find(userId: string): Promise<UserPreference[]> {
    const items = await this.userPreferencesStore.find((qb) => {
      qb.where('user-preference.userId = :userId', { userId });
      return qb;
    });
    return items.map((item) => this.validatePreference(item));
  }

  async findOneByPreference(
    userId: string,
    preference: PreferenceEnum,
  ): Promise<UserPreference | null> {
    const item = await this.userPreferencesStore.findOne((qb) => {
      qb.where(
        'user-preference.userId = :userId AND user-preference.preference = :preference',
        { userId, preference },
      );
      return qb;
    });

    if (!item) return null;

    return this.validatePreference(item);
  }

  async findOneByPreferenceOrThrow(
    userId: string,
    preference: PreferenceEnum,
  ): Promise<UserPreference> {
    const item = await this.findOneByPreference(userId, preference);

    if (!item) {
      throw new NotFoundException(
        `A(z) "${preference}" preferencia nem található.`,
      );
    }

    return item;
  }

  async create(
    userId: string,
    payload: UserPreferenceToCreate,
  ): Promise<UserPreference> {
    const entity = this.userPreferencesStore.createEntity({
      userId,
      ...payload,
    });

    this.validatePreference(entity);

    const createdEntity =
      await this.userPreferencesStore.createOrUpdate(entity);

    return this.validatePreference(createdEntity);
  }

  async updateOne(
    userId: string,
    preference: PreferenceEnum,
    payload: UserPreferenceToUpdate,
    existing?: UserPreference,
  ): Promise<UserPreference> {
    let persistedTorrent = existing;

    if (!persistedTorrent) {
      persistedTorrent = await this.findOneByPreferenceOrThrow(
        userId,
        preference,
      );
    }

    const updateData = omitBy(payload, isUndefined);

    const validatedItem = this.validatePreference({
      ...persistedTorrent,
      ...updateData,
    });

    const entity = this.userPreferencesStore.createEntity(validatedItem);
    const updatedItem = await this.userPreferencesStore.createOrUpdate(entity);

    return this.validatePreference(updatedItem);
  }

  async deleteByPreference(
    userId: string,
    preference: PreferenceEnum,
  ): Promise<void> {
    try {
      const item = await this.findOneByPreferenceOrThrow(userId, preference);
      await this.userPreferencesStore.delete(item);
    } catch (error) {
      this.logger.error(
        `🚨 "${preference}" preferencia törlése közben hiba történt!`,
        error,
      );

      throw error;
    }
  }

  private validatePreference(preference: UserPreferenceEntity): UserPreference {
    const parsed = userPreferenceSchema.safeParse(preference);
    if (!parsed.success) {
      const details = parsed.error.issues
        .map((issue) => {
          const path = issue.path.join('.');
          return path ? `${path}: ${issue.message}` : issue.message;
        })
        .join('; ');
      throw new BadRequestException(details);
    }

    return parsed.data;
  }
}
