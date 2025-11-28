import { TrackerEnum } from '../enum/tracker.enum';

export interface TrackerCredentialToCreate {
  tracker: TrackerEnum;
  username: string;
  password: string;
}
