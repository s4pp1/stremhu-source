import type { Config } from 'jest';

const config: Config = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: 'src',
  testRegex: '.*\\.spec\\.ts$',
  transform: {
    '^.+\\.(t|j)s$': 'ts-jest',
  },
  collectCoverageFrom: ['**/*.(t|j)s'],
  coverageDirectory: '../coverage',
  testEnvironment: 'node',
  watchman: false,
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/$1',
  },
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: '.',
        outputName: 'junit.xml',
      },
    ],
  ],
  transformIgnorePatterns: [
    'node_modules/(?!(axios-cookiejar-support|http-cookie-agent|http-proxy-agent|https-proxy-agent)/)',
  ],
};

export default config;
