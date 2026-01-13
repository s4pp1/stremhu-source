import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { DeepPartial, EntityManager, Repository } from 'typeorm';

import { Setting } from '../entity/setting.entity';
import { APP_SETTINGS, TORRENT_SETTINGS } from '../settings.constant';

@Injectable()
export class SettingsStore {
  constructor(
    @InjectRepository(Setting)
    private readonly settingRepository: Repository<Setting>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<Setting> {
    return manager ? manager.getRepository(Setting) : this.settingRepository;
  }

  createEntity(data: DeepPartial<Setting>): Setting {
    const entity = this.settingRepository.create(data);
    return entity;
  }
  async createOrUpdate(
    entity: Setting,
    manager?: EntityManager,
  ): Promise<Setting> {
    const repository = this.getRepository(manager);
    const setting = await repository.save(entity);
    return setting;
  }

  async findOneByKey(
    key: typeof APP_SETTINGS | typeof TORRENT_SETTINGS,
  ): Promise<Setting | null> {
    const setting = await this.settingRepository.findOne({
      where: { key },
    });

    return setting;
  }
}
