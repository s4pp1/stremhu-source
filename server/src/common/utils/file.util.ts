import { partial } from 'filesize';
import { Dirent } from 'node:fs';
import { readFile, readdir } from 'node:fs/promises';

export async function safeReaddir(dir: string): Promise<Dirent[]> {
  try {
    return await readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

export async function safeReadFile(
  path: string,
): Promise<Buffer<ArrayBuffer> | null> {
  try {
    const fileBuffer = await readFile(path);
    return fileBuffer;
  } catch {
    return null;
  }
}

export const formatFilesize = partial({ standard: 'jedec' });
