# Auth Testing Playbook — Fase 0

## Credenciales demo (seed idempotente al startup)
- admin@metanosrgan.co / Admin123!      → role `admin`
- analista@metanosrgan.co / Analista123! → role `analyst`
- visor@metanosrgan.co / Visor123!       → role `viewer`

## Mongo verification
```
mongosh
use metanosrgan_db
db.users.countDocuments()                // 3
db.stations.countDocuments()             // 5
db.users.findOne({role:"admin"},{password_hash:1})  // hash debe empezar con $2b$
```

## API smoke (curl contra 127.0.0.1:8001)
```
BASE=http://localhost:8001
curl -s $BASE/api/health
curl -s -X POST $BASE/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@metanosrgan.co","password":"Admin123!"}'
TOKEN=<paste>
curl -s $BASE/api/auth/me -H "Authorization: Bearer $TOKEN"
curl -s $BASE/api/stations | python3 -m json.tool | head -30
```

## Script
`bash /app/scripts/smoke.sh`  — corre health + login(ok/wrong) + me(ok/unauth) + stations==5.
