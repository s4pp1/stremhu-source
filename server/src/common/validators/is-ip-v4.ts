import {
  ValidatorConstraint,
  ValidatorConstraintInterface,
} from 'class-validator';
import { Address4 } from 'ip-address';

@ValidatorConstraint({ name: 'NoPathDomain', async: false })
export class IsIPv4 implements ValidatorConstraintInterface {
  validate(value: string) {
    return new Address4(value).isCorrect();
  }
  defaultMessage() {
    return 'Csak IPv4 megadása lehetséges (pl.: 192.168.1.100)';
  }
}
