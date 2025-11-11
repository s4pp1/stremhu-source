import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { EntityManager, Repository } from 'typeorm';

import { WebTorrentService } from 'src/web-torrent/web-torrent.service';

import { TrackerEnum } from '../enums/tracker.enum';
import { TrackerCredential } from './entities/tracker-credential.entity';
import { TrackerCredentialToCreate } from './tracker-credentials.types';

@Injectable()
export class TrackerCredentialsService {
  constructor(
    @InjectRepository(TrackerCredential)
    private trackerCredentialRepository: Repository<TrackerCredential>,
    private webTorrentService: WebTorrentService,
  ) {}

  protected getRepository(
    manager?: EntityManager,
  ): Repository<TrackerCredential> {
    return manager
      ? manager.getRepository(TrackerCredential)
      : this.trackerCredentialRepository;
  }

  async create(
    payload: TrackerCredentialToCreate,
    manager?: EntityManager,
  ): Promise<TrackerCredential> {
    const repository = this.getRepository(manager);
    const trackerCredentialEntity = repository.create(payload);
    return repository.save(trackerCredentialEntity);
  }

  async find(): Promise<TrackerCredential[]> {
    const trackerCredentials = await this.trackerCredentialRepository.find();
    return trackerCredentials;
  }

  async findOne(tracker: TrackerEnum): Promise<TrackerCredential | null> {
    const trackerCredential = await this.trackerCredentialRepository.findOne({
      where: { tracker },
    });
    return trackerCredential;
  }

  async findOneOrThrow(tracker: TrackerEnum): Promise<TrackerCredential> {
    const credential = await this.findOne(tracker);

    if (!credential) {
      throw new NotFoundException(`${tracker} nem található`);
    }

    return credential;
  }

  async delete(tracker: TrackerEnum, manager?: EntityManager): Promise<void> {
    const credential = await this.findOneOrThrow(tracker);

    const repository = this.getRepository(manager);
    await repository.remove(credential);

    await this.webTorrentService.deleteAllByTracker(tracker);
  }
}
