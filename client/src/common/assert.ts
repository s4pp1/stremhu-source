export function assertExists<T>(value: T): asserts value is NonNullable<T> {
  if (!value) {
    throw new Error('A store nem érhető el!')
  }
}
