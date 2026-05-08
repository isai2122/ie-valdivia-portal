# MetanoSRGAN Elite v5.5 — Test Credentials

## 🔐 Admin Principal (creado automáticamente al arranque)

```
Email/Usuario:  ortizisacc18@gmail.com  (o "ortizisacc18")
Password:       212228IsaiJosias@
Rol:            admin (control total)
```

> ⚠️ **NO compartir esta contraseña**. Cambiarla en producción mediante el panel admin.
> Login en: `/login` → redirige automáticamente a `/admin` para administradores y a `/app` para usuarios.

## 👥 Usuarios de demostración (creados durante testing)

```
Plan REGIONAL ($800/mes):
  Email:    jr@ecopetrol.com
  Username: ecopetrol_jr
  Password: Ecopetrol2026!
  Empresa:  Ecopetrol

Plan ENTERPRISE ($8,000/mes):
  Email:    enterprise@ecopetrol.com
  Username: ecopetrol_enterprise
  Password: Enterprise2026!
  Empresa:  Ecopetrol
```

## 🌐 Rutas

| Ruta | Descripción |
|------|-------------|
| `/` | Auto-redirect: si hay sesión → `/admin` o `/app`; si no → `/login` |
| `/login` | Pantalla de autenticación (sin credenciales expuestas) |
| `/admin` | Panel de administración (solo admins) |
| `/app` | Dashboard de usuario (con feature gating por plan) |
| `/api/docs` | Swagger / OpenAPI |

## 🔌 Test rápido

```bash
API="https://wingman-29b255c3-66da-47d4-b4ef-fc21ee142b5a.preview.emergentagent.com"

# Login admin
curl -X POST $API/api/auth/login -H "Content-Type: application/json" \
  -d '{"username":"ortizisacc18@gmail.com","password":"212228IsaiJosias@"}'

# Login usuario regional
curl -X POST $API/api/auth/login -H "Content-Type: application/json" \
  -d '{"username":"jr@ecopetrol.com","password":"Ecopetrol2026!"}'

# Listar planes (público)
curl $API/api/v55/plans

# Mi plan (autenticado)
curl $API/api/v55/plans/me -H "Authorization: Bearer <TOKEN>"
```
