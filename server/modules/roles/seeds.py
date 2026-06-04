from modules.roles.constants import UserRoleKey
from modules.roles.models import RoleModel

DEFAULT_ROLES = [
    RoleModel(id=UserRoleKey.ADMIN, name="Adminisztrátor"),
    RoleModel(id=UserRoleKey.USER, name="Felhasználó"),
]
