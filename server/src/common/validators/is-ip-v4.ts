import {
  ValidatorConstraint,
  ValidatorConstraintInterface,
} from 'class-validator';
import { Address4 } from 'ip-address';

@ValidatorConstraint({ name: 'NoPathDomain', async: false })
export class IsIPv4 implements ValidatorConstraintInterface {
  validate(value: string) {
    try {
      new Address4(value);
      if (value.includes('/') || value.includes(':')) {
        return false;
      }

      return true;
    } catch {
      return false;
    }
  }
  defaultMessage() {
    return 'Csak IPv4 megadása lehetséges (pl.: 192.168.1.100)';
  }
}
