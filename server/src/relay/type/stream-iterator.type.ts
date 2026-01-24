import { CreateReadStream } from './create-read-stream.type';

export type StreamIterator = CreateReadStream & {
  stremId: string;
};
