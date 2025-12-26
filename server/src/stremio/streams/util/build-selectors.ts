export function buildSelectors<T extends string>(userPriority: T[]) {
  const allowSet = new Set(userPriority);

  const rankMap = Object.fromEntries(
    userPriority.map((resolution, index) => [resolution, index]),
  ) as Record<T, number>;

  return {
    filterToAllowed: (resolution: T) => allowSet.has(resolution),
    priorityIndex: (allowedResolution: T) => rankMap[allowedResolution],
  };
}
