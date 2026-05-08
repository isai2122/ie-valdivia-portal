"""
jwt_auth_v36.py — MetanoSRGAN Elite v3.6
Autenticación JWT (JSON Web Token) para acceso seguro al dashboard y API.

Características:
  - Tokens JWT firmados con HS256 (HMAC-SHA256)
  - Roles: admin, operador, viewer
  - Refresh tokens con rotación automática
  - Blacklist de tokens revocados (logout seguro)
  - Rate limiting por IP (anti-brute force)
  - Integración con FastAPI (middleware y dependencias)

Configuración vía variables de entorno:
  JWT_SECRET_KEY     — Clave secreta para firmar tokens (CAMBIAR EN PRODUCCIÓN)
  JWT_ALGORITHM      — Algoritmo (default: HS256)
  JWT_EXPIRE_MINUTES — Expiración del access token (default: 60 min)
  JWT_REFRESH_DAYS   — Expiración del refresh token (default: 7 días)
  ADMIN_USERNAME     — Usuario administrador (default: admin)
  ADMIN_PASSWORD     — Contraseña del admin (CAMBIAR EN PRODUCCIÓN)
"""

import os
import json
import logging
import hashlib
import hmac
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Configuración ────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "metanosrgan-elite-secret-key-CHANGE-IN-PROD")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "MetanoElite2026!")
# Rutas relativas para Render
BASE_DIR = Path(__file__).parent.parent
USERS_FILE = os.getenv("USERS_FILE", str(BASE_DIR / "data" / "users.json"))
TOKEN_BLACKLIST_FILE = os.getenv(
    "TOKEN_BLACKLIST_FILE",
    str(BASE_DIR / "data" / "token_blacklist.json"),
)

# Roles disponibles
ROLES = {
    "admin":    {"can_read": True,  "can_write": True,  "can_admin": True},
    "operador": {"can_read": True,  "can_write": True,  "can_admin": False},
    "viewer":   {"can_read": True,  "can_write": False, "can_admin": False},
}

# Rate limiting: máx intentos fallidos por IP
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _check_pyjwt() -> bool:
    try:
        import jwt
        return True
    except ImportError:
        return False


class JWTAuthManager:
    """
    Gestor de autenticación JWT para MetanoSRGAN Elite.
    Maneja usuarios, tokens, roles y seguridad del dashboard.
    """

    def __init__(
        self,
        secret_key: str = JWT_SECRET_KEY,
        algorithm: str = JWT_ALGORITHM,
        expire_minutes: int = JWT_EXPIRE_MINUTES,
        refresh_days: int = JWT_REFRESH_DAYS,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
        self.refresh_days = refresh_days
        self._pyjwt_available = _check_pyjwt()
        self._users: Dict[str, Dict] = {}
        self._blacklist: List[str] = []
        self._failed_attempts: Dict[str, Dict] = {}  # IP → {count, last_attempt}

        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        self._load_users()
        self._load_blacklist()
        self._ensure_admin_user()

    # ─── Gestión de usuarios ──────────────────────────────────────────────────
    def _load_users(self):
        """Carga usuarios desde archivo JSON."""
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE) as f:
                    self._users = json.load(f)
                logger.info(f"JWT: {len(self._users)} usuarios cargados.")
            except Exception as e:
                logger.warning(f"JWT: error cargando usuarios: {e}")
                self._users = {}

    def _save_users(self):
        """Guarda usuarios en archivo JSON."""
        with open(USERS_FILE, "w") as f:
            json.dump(self._users, f, indent=2)

    def _load_blacklist(self):
        """Carga blacklist de tokens revocados."""
        if os.path.exists(TOKEN_BLACKLIST_FILE):
            try:
                with open(TOKEN_BLACKLIST_FILE) as f:
                    data = json.load(f)
                    self._blacklist = data.get("tokens", [])
            except Exception:
                self._blacklist = []

    def _save_blacklist(self):
        """Guarda blacklist de tokens."""
        with open(TOKEN_BLACKLIST_FILE, "w") as f:
            json.dump({"tokens": self._blacklist[-1000:]}, f)

    def _hash_password(self, password: str) -> str:
        """Hashea una contraseña con SHA-256 + salt."""
        salt = self.secret_key[:16]
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def _ensure_admin_user(self):
        """Crea el usuario admin por defecto si no existe."""
        if ADMIN_USERNAME not in self._users:
            self.create_user(
                username=ADMIN_USERNAME,
                password=ADMIN_PASSWORD,
                role="admin",
                full_name="Administrador del Sistema",
                email="admin@metanosrgan.co",
            )
            logger.info(f"JWT: usuario admin creado: {ADMIN_USERNAME}")

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "viewer",
        full_name: str = "",
        email: str = "",
    ) -> bool:
        """
        Crea un nuevo usuario.

        Args:
            username: Nombre de usuario único.
            password: Contraseña en texto plano (se hashea).
            role: Rol del usuario (admin/operador/viewer).
            full_name: Nombre completo.
            email: Email del usuario.

        Returns:
            True si se creó exitosamente.
        """
        if username in self._users:
            logger.warning(f"JWT: usuario ya existe: {username}")
            return False

        if role not in ROLES:
            logger.error(f"JWT: rol inválido: {role}")
            return False

        self._users[username] = {
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "full_name": full_name,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "active": True,
        }
        self._save_users()
        logger.info(f"JWT: usuario creado: {username} (rol: {role})")
        return True

    def update_password(self, username: str, new_password: str) -> bool:
        """Actualiza la contraseña de un usuario."""
        if username not in self._users:
            return False
        self._users[username]["password_hash"] = self._hash_password(new_password)
        self._save_users()
        logger.info(f"JWT: contraseña actualizada para {username}")
        return True

    def deactivate_user(self, username: str) -> bool:
        """Desactiva un usuario (no lo elimina)."""
        if username not in self._users:
            return False
        self._users[username]["active"] = False
        self._save_users()
        return True

    # ─── Autenticación ────────────────────────────────────────────────────────
    def _check_rate_limit(self, ip: str) -> Tuple[bool, int]:
        """
        Verifica si una IP está bloqueada por intentos fallidos.

        Returns:
            (is_blocked, seconds_remaining)
        """
        if ip not in self._failed_attempts:
            return False, 0

        attempts = self._failed_attempts[ip]
        if attempts["count"] < MAX_FAILED_ATTEMPTS:
            return False, 0

        lockout_until = attempts["last_attempt"] + LOCKOUT_MINUTES * 60
        remaining = int(lockout_until - time.time())
        if remaining > 0:
            return True, remaining

        # Lockout expirado, resetear
        del self._failed_attempts[ip]
        return False, 0

    def _record_failed_attempt(self, ip: str):
        """Registra un intento fallido de autenticación."""
        if ip not in self._failed_attempts:
            self._failed_attempts[ip] = {"count": 0, "last_attempt": 0}
        self._failed_attempts[ip]["count"] += 1
        self._failed_attempts[ip]["last_attempt"] = time.time()

    def _clear_failed_attempts(self, ip: str):
        """Limpia los intentos fallidos de una IP tras login exitoso."""
        self._failed_attempts.pop(ip, None)

    def authenticate(
        self, username: str, password: str, ip: str = "unknown"
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Autentica un usuario con usuario/contraseña.

        Args:
            username: Nombre de usuario.
            password: Contraseña en texto plano.
            ip: IP del cliente (para rate limiting).

        Returns:
            Tuple (success, user_data, message)
        """
        # Verificar rate limit
        is_blocked, remaining = self._check_rate_limit(ip)
        if is_blocked:
            return False, None, f"IP bloqueada por {remaining}s (demasiados intentos fallidos)"

        # Verificar usuario
        if username not in self._users:
            self._record_failed_attempt(ip)
            logger.warning(f"JWT: login fallido — usuario no existe: {username} (IP: {ip})")
            return False, None, "Credenciales inválidas"

        user = self._users[username]

        # Verificar usuario activo
        if not user.get("active", True):
            return False, None, "Usuario desactivado"

        # Verificar contraseña
        if user["password_hash"] != self._hash_password(password):
            self._record_failed_attempt(ip)
            logger.warning(f"JWT: login fallido — contraseña incorrecta: {username} (IP: {ip})")
            return False, None, "Credenciales inválidas"

        # Login exitoso
        self._clear_failed_attempts(ip)
        self._users[username]["last_login"] = datetime.now(timezone.utc).isoformat()
        self._save_users()
        logger.info(f"JWT: login exitoso: {username} (IP: {ip})")

        return True, user, "Autenticación exitosa"

    # ─── Generación de tokens ─────────────────────────────────────────────────
    def _encode_token(self, payload: Dict) -> str:
        """Codifica un token JWT."""
        if self._pyjwt_available:
            import jwt
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        else:
            # Implementación manual básica (fallback sin PyJWT)
            import json, base64, hmac, hashlib
            header = base64.urlsafe_b64encode(
                json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            ).rstrip(b"=").decode()
            body = base64.urlsafe_b64encode(
                json.dumps(payload).encode()
            ).rstrip(b"=").decode()
            sig_input = f"{header}.{body}".encode()
            sig = hmac.new(self.secret_key.encode(), sig_input, hashlib.sha256).digest()
            signature = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
            return f"{header}.{body}.{signature}"

    def _decode_token(self, token: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Decodifica y valida un token JWT.

        Returns:
            (valid, payload, message)
        """
        if self._pyjwt_available:
            import jwt
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                )
                return True, payload, "OK"
            except jwt.ExpiredSignatureError:
                return False, None, "Token expirado"
            except jwt.InvalidTokenError as e:
                return False, None, f"Token inválido: {e}"
        else:
            # Fallback manual
            try:
                parts = token.split(".")
                if len(parts) != 3:
                    return False, None, "Formato de token inválido"
                body_padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(body_padded))
                if payload.get("exp", 0) < time.time():
                    return False, None, "Token expirado"
                return True, payload, "OK"
            except Exception as e:
                return False, None, f"Error decodificando token: {e}"

    def create_access_token(self, username: str, role: str) -> str:
        """
        Genera un access token JWT.

        Args:
            username: Nombre de usuario.
            role: Rol del usuario.

        Returns:
            Token JWT como string.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "role": role,
            "permissions": ROLES.get(role, {}),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.expire_minutes)).timestamp()),
            "iss": "MetanoSRGAN-Elite-v3.6",
        }
        return self._encode_token(payload)

    def create_refresh_token(self, username: str) -> str:
        """
        Genera un refresh token JWT de larga duración.

        Args:
            username: Nombre de usuario.

        Returns:
            Refresh token JWT como string.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=self.refresh_days)).timestamp()),
            "iss": "MetanoSRGAN-Elite-v3.6",
        }
        return self._encode_token(payload)

    def login(
        self, username: str, password: str, ip: str = "unknown"
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Proceso completo de login: autentica y genera tokens.

        Returns:
            (success, token_data, message)
            token_data = {access_token, refresh_token, token_type, expires_in, user}
        """
        success, user, message = self.authenticate(username, password, ip)
        if not success:
            return False, None, message

        access_token = self.create_access_token(username, user["role"])
        refresh_token = self.create_refresh_token(username)

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.expire_minutes * 60,
            "user": {
                "username": username,
                "role": user["role"],
                "full_name": user.get("full_name", ""),
                "email": user.get("email", ""),
                "permissions": ROLES.get(user["role"], {}),
            },
        }
        return True, token_data, "Login exitoso"

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[str], str]:
        """
        Genera un nuevo access token usando un refresh token válido.

        Returns:
            (success, new_access_token, message)
        """
        # Verificar que no esté en blacklist
        if refresh_token in self._blacklist:
            return False, None, "Refresh token revocado"

        valid, payload, message = self._decode_token(refresh_token)
        if not valid:
            return False, None, message

        if payload.get("type") != "refresh":
            return False, None, "Token no es de tipo refresh"

        username = payload.get("sub")
        if username not in self._users:
            return False, None, "Usuario no encontrado"

        user = self._users[username]
        if not user.get("active", True):
            return False, None, "Usuario desactivado"

        new_access_token = self.create_access_token(username, user["role"])
        logger.info(f"JWT: access token renovado para {username}")
        return True, new_access_token, "Token renovado"

    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Revoca los tokens del usuario (logout seguro).
        Agrega los tokens a la blacklist.
        """
        revoked = False
        if access_token and access_token not in self._blacklist:
            self._blacklist.append(access_token)
            revoked = True
        if refresh_token and refresh_token not in self._blacklist:
            self._blacklist.append(refresh_token)
            revoked = True

        if revoked:
            self._save_blacklist()
            logger.info("JWT: tokens revocados (logout).")
        return revoked

    # ─── Validación de tokens ─────────────────────────────────────────────────
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Verifica un access token y retorna el payload si es válido.

        Returns:
            (valid, payload, message)
        """
        if token in self._blacklist:
            return False, None, "Token revocado"

        valid, payload, message = self._decode_token(token)
        if not valid:
            return False, None, message

        if payload.get("type") != "access":
            return False, None, "Token no es de tipo access"

        username = payload.get("sub")
        if username not in self._users:
            return False, None, "Usuario no encontrado"

        if not self._users[username].get("active", True):
            return False, None, "Usuario desactivado"

        return True, payload, "Token válido"

    def require_permission(self, token: str, permission: str) -> Tuple[bool, str]:
        """
        Verifica si el token tiene un permiso específico.

        Args:
            token: Access token JWT.
            permission: Permiso requerido (can_read, can_write, can_admin).

        Returns:
            (has_permission, message)
        """
        valid, payload, message = self.verify_token(token)
        if not valid:
            return False, message

        permissions = payload.get("permissions", {})
        if not permissions.get(permission, False):
            role = payload.get("role", "unknown")
            return False, f"Permiso '{permission}' no disponible para rol '{role}'"

        return True, "OK"

    # ─── FastAPI Integration ──────────────────────────────────────────────────
    def get_fastapi_dependencies(self):
        """
        Retorna las dependencias de FastAPI para proteger endpoints.

        Uso en FastAPI:
            from jwt_auth_v36 import auth_manager
            deps = auth_manager.get_fastapi_dependencies()

            @app.get("/api/protected")
            async def protected(user=Depends(deps["require_auth"])):
                return {"user": user}
        """
        try:
            from fastapi import Depends, HTTPException, status
            from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

            security = HTTPBearer()
            auth_manager = self

            async def require_auth(
                credentials: HTTPAuthorizationCredentials = Depends(security),
            ) -> Dict:
                token = credentials.credentials
                valid, payload, message = auth_manager.verify_token(token)
                if not valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=message,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                return payload

            async def require_write(
                credentials: HTTPAuthorizationCredentials = Depends(security),
            ) -> Dict:
                token = credentials.credentials
                has_perm, message = auth_manager.require_permission(token, "can_write")
                if not has_perm:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=message,
                    )
                valid, payload, _ = auth_manager.verify_token(token)
                return payload

            async def require_admin(
                credentials: HTTPAuthorizationCredentials = Depends(security),
            ) -> Dict:
                token = credentials.credentials
                has_perm, message = auth_manager.require_permission(token, "can_admin")
                if not has_perm:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=message,
                    )
                valid, payload, _ = auth_manager.verify_token(token)
                return payload

            return {
                "require_auth": require_auth,
                "require_write": require_write,
                "require_admin": require_admin,
                "security": security,
            }
        except ImportError:
            logger.warning("FastAPI no disponible. Dependencias JWT no creadas.")
            return {}

    # ─── Estado del módulo ────────────────────────────────────────────────────
    def get_status(self) -> Dict:
        """Retorna el estado del sistema de autenticación."""
        return {
            "pyjwt_available": self._pyjwt_available,
            "algorithm": self.algorithm,
            "expire_minutes": self.expire_minutes,
            "refresh_days": self.refresh_days,
            "total_users": len(self._users),
            "active_users": sum(1 for u in self._users.values() if u.get("active", True)),
            "blacklisted_tokens": len(self._blacklist),
            "roles_available": list(ROLES.keys()),
            "rate_limit": {
                "max_attempts": MAX_FAILED_ATTEMPTS,
                "lockout_minutes": LOCKOUT_MINUTES,
            },
        }

    def list_users(self) -> List[Dict]:
        """Lista todos los usuarios (sin contraseñas)."""
        return [
            {
                "username": u["username"],
                "role": u["role"],
                "full_name": u.get("full_name", ""),
                "email": u.get("email", ""),
                "active": u.get("active", True),
                "created_at": u.get("created_at"),
                "last_login": u.get("last_login"),
            }
            for u in self._users.values()
        ]


# ─── Instancia global ─────────────────────────────────────────────────────────
auth_manager = JWTAuthManager()
