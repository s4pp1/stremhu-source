import {
  NetworkAutoSetupDto,
  NetworkManualSetupDto,
} from '../dto/network-setup.dto';

export type NetworkSetup = NetworkAutoSetupDto | NetworkManualSetupDto;
