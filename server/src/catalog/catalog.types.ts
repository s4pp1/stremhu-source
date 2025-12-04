export interface ResolveImdbId {
  imdbId: string;
  season?: number;
  episode?: number;
}

export interface ResolvedImdbId {
  imdbId: string;
  originalImdbId?: string;
}
