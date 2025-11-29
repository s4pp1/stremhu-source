import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { isUndefined, omitBy } from 'lodash';
import { EntityManager, Repository } from 'typeorm';

import { GLOBAL_ID } from 'src/common/common.constant';

import { Setting } from '../entity/setting.entity';
import { SettingToCreate, SettingToUpdate } from '../settings.types';

@Injectable()
export class SettingsStore {
  constructor(
    private readonly configService: ConfigService,
    @InjectRepository(Setting)
    private readonly settingRepository: Repository<Setting>,
  ) {}

  protected getRepository(manager?: EntityManager): Repository<Setting> {
    return manager ? manager.getRepository(Setting) : this.settingRepository;
  }

  async create(payload: SettingToCreate): Promise<Setting> {
    const settingEntity = this.settingRepository.create(payload);
    const setting = await this.settingRepository.save(settingEntity);

    return setting;
  }

  async findOne(): Promise<Setting | null> {
    const setting = await this.settingRepository.findOne({
      where: { id: GLOBAL_ID },
    });

    return setting;
  }

  async findOneOrThrow(): Promise<Setting> {
    const setting = await this.findOne();

    if (!setting) {
      throw new InternalServerErrorException('A beállítások nem érhetők el');
    }

    return setting;
  }

  async update(
    payload: SettingToUpdate,
    manager?: EntityManager,
  ): Promise<Setting> {
    const repository = this.getRepository(manager);

    const setting = await this.findOneOrThrow();

    const updateData = omitBy(payload, isUndefined);

    await repository.update({ id: GLOBAL_ID }, updateData);

    return { ...setting, ...updateData };
  }

  async getEndpoint() {
    const setting = await this.findOneOrThrow();

    let endpoint = this.buildLocalUrl('127.0.0.1');

    if (setting.enebledlocalIp && setting.address) {
      endpoint = this.buildLocalUrl(setting.address);
    }

    if (!setting.enebledlocalIp && setting.address) {
      endpoint = setting.address;
    }

    return endpoint;
  }

  buildLocalUrl(ipAddress: string) {
    const httpsPort = this.configService.getOrThrow<number>('app.https-port');
    return `https://${ipAddress.split('.').join('-')}.local-ip.medicmobile.org:${httpsPort}`;
  }
}
