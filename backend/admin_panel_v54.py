"""
admin_panel_v54.py — MetanoSRGAN Elite v5.4
============================================
Módulo de Administración de Usuarios con:
  - CRUD completo de usuarios (Crear, Leer, Actualizar, Eliminar)
  - Gestión de roles: Admin, Operador, Viewer
  - Asignación de activos a operadores
  - Reset de contraseñas
  - Auditoría de acciones administrativas
  - Integración con JWT v3.6 y Supabase
  - Protección por middleware require_admin

Admin: ortizisacc18@gmail.com
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Configuración ────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.parent
DATA_DIR  = BASE_DIR / "data"
AUDIT_LOG = DATA_DIR / "admin_audit_log.json"

os.makedirs(DATA_DIR, exist_ok=True)

# Activos disponibles en el sistema (Magdalena Medio)
ACTIVOS_DISPONIBLES = [
    "Pozo_MM_001", "Pozo_MM_002", "Pozo_MM_003", "Pozo_MM_004",
    "Pozo_MM_005", "Pozo_MM_006", "Pozo_MM_007", "Pozo_MM_008",
    "Estacion_Compresora_Norte", "Estacion_Compresora_Sur",
    "Oleoducto_Tramo_A", "Oleoducto_Tramo_B", "Oleoducto_Tramo_C",
    "Planta_Tratamiento_MM", "Terminal_Barrancabermeja",
    "Campo_Casabe", "Campo_Infantas", "Campo_La_Cira",
    "Gasoducto_Transversal", "Estacion_Bombeo_Central",
]

# Permisos por rol
ROLE_PERMISSIONS = {
    "admin": {
        "can_read":       True,
        "can_write":      True,
        "can_admin":      True,
        "can_delete":     True,
        "can_reset_pass": True,
        "can_assign":     True,
        "description":    "Control total del sistema",
        "color":          "#ff2244",
        "icon":           "👑",
    },
    "operador": {
        "can_read":       True,
        "can_write":      True,
        "can_admin":      False,
        "can_delete":     False,
        "can_reset_pass": False,
        "can_assign":     False,
        "description":    "Gestión de tickets y detecciones asignadas",
        "color":          "#ff8c00",
        "icon":           "🔧",
    },
    "viewer": {
        "can_read":       True,
        "can_write":      False,
        "can_admin":      False,
        "can_delete":     False,
        "can_reset_pass": False,
        "can_assign":     False,
        "description":    "Solo lectura del dashboard",
        "color":          "#00d4ff",
        "icon":           "👁️",
    },
}


class AdminPanelManager:
    """
    Gestor del Panel de Administración de MetanoSRGAN Elite v5.4.
    Proporciona CRUD de usuarios, gestión de roles y auditoría.
    """

    def __init__(self, auth_manager):
        self.auth = auth_manager
        self._audit_log: List[Dict] = []
        self._load_audit_log()
        logger.info("AdminPanelManager v5.4 inicializado")

    # ─── Auditoría ────────────────────────────────────────────────────────────

    def _load_audit_log(self):
        """Carga el log de auditoría desde disco."""
        if AUDIT_LOG.exists():
            try:
                with open(AUDIT_LOG) as f:
                    self._audit_log = json.load(f)
            except Exception as e:
                logger.warning(f"Error cargando audit log: {e}")
                self._audit_log = []

    def _save_audit_log(self):
        """Persiste el log de auditoría."""
        try:
            with open(AUDIT_LOG, "w") as f:
                json.dump(self._audit_log[-500:], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando audit log: {e}")

    def _audit(self, admin_user: str, action: str, target: str, details: str = ""):
        """Registra una acción administrativa."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "admin":     admin_user,
            "action":    action,
            "target":    target,
            "details":   details,
        }
        self._audit_log.append(entry)
        self._save_audit_log()
        logger.info(f"AUDIT [{admin_user}] {action} → {target}: {details}")

    # ─── Gestión de Usuarios ──────────────────────────────────────────────────

    def get_all_users(self) -> List[Dict]:
        """Retorna todos los usuarios con información completa (sin contraseñas)."""
        users = []
        for username, data in self.auth._users.items():
            role = data.get("role", "viewer")
            perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"])
            users.append({
                "username":    username,
                "email":       data.get("email", ""),
                "full_name":   data.get("full_name", ""),
                "role":        role,
                "role_icon":   perms["icon"],
                "role_color":  perms["color"],
                "role_desc":   perms["description"],
                "active":      data.get("active", True),
                "plan":        data.get("plan", "regional"),
                "empresa":     data.get("empresa", ""),
                "activos_asignados": data.get("activos_asignados", []),
                "created_at":  data.get("created_at", ""),
                "last_login":  data.get("last_login", ""),
                "permissions": {
                    k: v for k, v in perms.items()
                    if k.startswith("can_")
                },
            })
        return sorted(users, key=lambda u: (u["role"] != "admin", u["username"]))

    def create_user(
        self,
        admin_user: str,
        username: str,
        password: str,
        email: str = "",
        full_name: str = "",
        role: str = "viewer",
        plan: str = "regional",
        empresa: str = "",
        activos_asignados: Optional[List[str]] = None,
    ) -> Dict:
        """Crea un nuevo usuario en el sistema."""
        if role not in ROLE_PERMISSIONS:
            return {"success": False, "message": f"Rol inválido. Roles válidos: {list(ROLE_PERMISSIONS.keys())}"}

        if username in self.auth._users:
            return {"success": False, "message": f"El usuario '{username}' ya existe"}

        if len(password) < 8:
            return {"success": False, "message": "La contraseña debe tener al menos 8 caracteres"}

        # jwt_auth_v36 create_user retorna bool
        ok = self.auth.create_user(
            username=username,
            password=password,
            role=role,
            full_name=full_name,
            email=email,
        )

        if ok:
            u = self.auth._users[username]
            if activos_asignados:
                u["activos_asignados"] = activos_asignados
            u["plan"] = plan or "regional"
            u["empresa"] = empresa or ""
            u["plan_asignado_por"] = admin_user
            u["plan_asignado_en"] = datetime.now(timezone.utc).isoformat()
            self.auth._save_users()
            self._audit(admin_user, "CREATE_USER", username,
                        f"rol={role} plan={plan} empresa={empresa} activos={activos_asignados or []}")
            return {"success": True, "message": f"Usuario '{username}' creado con plan '{plan}'"}
        else:
            return {"success": False, "message": f"No se pudo crear el usuario '{username}'"}

    def update_user(
        self,
        admin_user: str,
        username: str,
        updates: Dict,
    ) -> Dict:
        """Actualiza datos de un usuario existente."""
        if username not in self.auth._users:
            return {"success": False, "message": f"Usuario '{username}' no encontrado"}

        user_data = self.auth._users[username]
        changed = []

        # Campos actualizables
        if "full_name" in updates:
            user_data["full_name"] = updates["full_name"]
            changed.append("full_name")

        if "email" in updates:
            user_data["email"] = updates["email"]
            changed.append("email")

        if "role" in updates:
            new_role = updates["role"]
            if new_role not in ROLE_PERMISSIONS:
                return {"success": False, "message": f"Rol inválido: {new_role}"}
            if username == admin_user and new_role != "admin":
                return {"success": False, "message": "No puedes cambiar tu propio rol de admin"}
            user_data["role"] = new_role
            changed.append(f"role={new_role}")

        if "activos_asignados" in updates:
            activos = updates["activos_asignados"]
            user_data["activos_asignados"] = activos
            changed.append(f"activos={activos}")

        if "active" in updates:
            if username == admin_user:
                return {"success": False, "message": "No puedes desactivarte a ti mismo"}
            user_data["active"] = bool(updates["active"])
            changed.append(f"active={updates['active']}")

        if "plan" in updates:
            user_data["plan"] = updates["plan"]
            user_data["plan_asignado_por"] = admin_user
            user_data["plan_asignado_en"] = datetime.now(timezone.utc).isoformat()
            changed.append(f"plan={updates['plan']}")

        if "empresa" in updates:
            user_data["empresa"] = updates["empresa"]
            changed.append(f"empresa={updates['empresa']}")

        self.auth._save_users()
        self._audit(admin_user, "UPDATE_USER", username, ", ".join(changed))

        return {"success": True, "message": f"Usuario '{username}' actualizado: {', '.join(changed)}"}

    def delete_user(self, admin_user: str, username: str) -> Dict:
        """Elimina (desactiva permanentemente) un usuario."""
        if username not in self.auth._users:
            return {"success": False, "message": f"Usuario '{username}' no encontrado"}

        if username == admin_user:
            return {"success": False, "message": "No puedes eliminarte a ti mismo"}

        # Desactivar en lugar de borrar para preservar auditoría
        self.auth._users[username]["active"] = False
        self.auth._users[username]["deleted_at"] = datetime.now(timezone.utc).isoformat()
        self.auth._save_users()
        self._audit(admin_user, "DELETE_USER", username, "Usuario desactivado permanentemente")

        return {"success": True, "message": f"Usuario '{username}' eliminado del sistema"}

    def reset_password(self, admin_user: str, username: str, new_password: str) -> Dict:
        """Resetea la contraseña de un usuario."""
        if username not in self.auth._users:
            return {"success": False, "message": f"Usuario '{username}' no encontrado"}

        if len(new_password) < 8:
            return {"success": False, "message": "La contraseña debe tener al menos 8 caracteres"}

        # Hashear nueva contraseña
        try:
            import bcrypt
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            hashed = hashlib.sha256(new_password.encode()).hexdigest()

        self.auth._users[username]["password_hash"] = hashed
        self.auth._users[username]["password_reset_at"] = datetime.now(timezone.utc).isoformat()
        self.auth._save_users()
        self._audit(admin_user, "RESET_PASSWORD", username, "Contraseña reseteada por admin")

        return {"success": True, "message": f"Contraseña de '{username}' reseteada exitosamente"}

    def assign_assets(self, admin_user: str, username: str, activos: List[str]) -> Dict:
        """Asigna activos específicos a un operador."""
        if username not in self.auth._users:
            return {"success": False, "message": f"Usuario '{username}' no encontrado"}

        # Validar activos
        invalid = [a for a in activos if a not in ACTIVOS_DISPONIBLES]
        if invalid:
            return {"success": False, "message": f"Activos inválidos: {invalid}"}

        self.auth._users[username]["activos_asignados"] = activos
        self.auth._save_users()
        self._audit(admin_user, "ASSIGN_ASSETS", username, f"Activos: {activos}")

        return {"success": True, "message": f"{len(activos)} activos asignados a '{username}'"}

    def toggle_user_status(self, admin_user: str, username: str) -> Dict:
        """Activa o desactiva un usuario."""
        if username not in self.auth._users:
            return {"success": False, "message": f"Usuario '{username}' no encontrado"}

        if username == admin_user:
            return {"success": False, "message": "No puedes desactivarte a ti mismo"}

        current = self.auth._users[username].get("active", True)
        self.auth._users[username]["active"] = not current
        self.auth._save_users()

        action = "ACTIVATE_USER" if not current else "DEACTIVATE_USER"
        self._audit(admin_user, action, username, f"Estado: {not current}")

        status_str = "activado" if not current else "desactivado"
        return {"success": True, "message": f"Usuario '{username}' {status_str}"}

    # ─── Estadísticas ─────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Retorna estadísticas del panel de administración."""
        users = list(self.auth._users.values())
        return {
            "total_usuarios":    len(users),
            "usuarios_activos":  sum(1 for u in users if u.get("active", True)),
            "usuarios_inactivos": sum(1 for u in users if not u.get("active", True)),
            "admins":            sum(1 for u in users if u.get("role") == "admin"),
            "operadores":        sum(1 for u in users if u.get("role") == "operador"),
            "viewers":           sum(1 for u in users if u.get("role") == "viewer"),
            "total_activos":     len(ACTIVOS_DISPONIBLES),
            "acciones_auditadas": len(self._audit_log),
        }

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Retorna el log de auditoría más reciente."""
        return list(reversed(self._audit_log[-limit:]))

    def get_available_assets(self) -> List[str]:
        """Retorna la lista de activos disponibles para asignación."""
        return ACTIVOS_DISPONIBLES

    def get_roles_info(self) -> Dict:
        """Retorna información detallada de los roles disponibles."""
        return ROLE_PERMISSIONS
