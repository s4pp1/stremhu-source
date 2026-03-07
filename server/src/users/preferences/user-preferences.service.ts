import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { difference, isUndefined, omitBy } from 'lodash';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

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
      qb.where('user-preference.userId = :userId', { userId }).orderBy({
        'user-preference.order': 'ASC',
      });

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
    if (payload.blocked.length === 0 && payload.preferred.length === 0) {
      throw new BadRequestException(
        'A blocked vagy preferred megadása kötelező.',
      );
    }

    const userPreferences = await this.find(userId);

    let order: number | null = null;

    if (payload.preferred.length !== 0) {
      const orderedUserPreferences = userPreferences.filter(
        (userPreference) => userPreference.order !== null,
      );
      order = orderedUserPreferences.length - 1;
    }

    const entity = this.userPreferencesStore.createEntity({
      ...payload,
      userId,
      order,
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

    await this.reorder(userId);
  }

  async deletePreferenceTrackerItem(trackerEnum: TrackerEnum) {
    try {
      const items = await this.userPreferencesStore.find((qb) => {
        qb.where('user-preference.preference = :preference', {
          preference: PreferenceEnum.TRACKER,
        });
        return qb;
      });

      if (items.length === 0) {
        return;
      }

      for (const item of items) {
        const preferred = item.preferred.filter((pref) => pref !== trackerEnum);
        const blocked = item.blocked.filter((pref) => pref !== trackerEnum);

        if (preferred.length === 0 && blocked.length === 0) {
          await this.deleteByPreference(item.userId, PreferenceEnum.TRACKER);
        } else {
          await this.updateOne(item.userId, PreferenceEnum.TRACKER, {
            blocked,
            preferred,
          });
        }
      }
    } catch (error) {
      this.logger.error(
        `🚨 A "${trackerEnum}" törlése közben hiba történt!`,
        error,
      );

      throw error;
    }
  }

  async reorder(
    userId: string,
    preferences?: PreferenceEnum[],
  ): Promise<UserPreference[]> {
    const items = await this.userPreferencesStore.find((qb) => {
      qb.where(
        'user-preference.userId = :userId AND user-preference.order IS NOT NULL',
        { userId },
      ).orderBy({
        'user-preference.order': 'ASC',
      });

      return qb;
    });

    let itemIds = items.map((item) => item.preference);

    if (preferences !== undefined) {
      const diffItems = difference(itemIds, preferences);
      if (diffItems.length > 0) {
        throw new BadRequestException(
          `A "${diffItems.join(', ')}" nem található.`,
        );
      }

      itemIds = preferences;
    }

    await Promise.all(
      itemIds.map((preference, idx) =>
        this.updateOne(userId, preference, { order: idx }),
      ),
    );

    return this.find(userId);
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
