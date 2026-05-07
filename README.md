# IE Valdivia - Portal Educativo

Full-stack school portal: React frontend + FastAPI backend + MongoDB Atlas. Single URL deployment on Render.

## Stack
- Frontend: React 19 + React Router + Tailwind CSS + lucide-react
- Backend: FastAPI + Motor (async MongoDB driver)
- Database: MongoDB Atlas (cloud)
- Hosting: Render (single Web Service serves both frontend build and `/api/*`)

## Features
- Public pages: Inicio, Noticias, Proyectos, Videos, Sobre Nosotros, Perfil
- Admin login (user `admin`, default password `12`) with floating side panel for editing:
  logo, banners (image or video), news, projects, videos, about us, social links, site config, **change admin password**
- Banners support YouTube/Vimeo/.mp4 videos with autoplay/mute/loop
- Videos page with grid + modal player (YouTube embed or direct video)
- Site auto-refreshes every 15s so admin changes propagate to all visitors
- Search across news, projects, videos

## Deployment to Render (recommended path for IA Manus)

### Prerequisites
1. **MongoDB Atlas** account with a free cluster (M0). Make sure:
   - You created a database user with username + password
   - Network Access has `0.0.0.0/0` allowed (so Render can connect)
   - You copied the connection string in the form:
     ```
     mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
2. A **GitHub repository** containing this project (push the whole `/app` content to a repo).

### Steps Manus IA must follow
1. Open https://dashboard.render.com and sign in / create an account.
2. Click **New +** → **Blueprint**.
3. Connect the GitHub repository where this project was pushed.
4. Render will detect `render.yaml` automatically. Confirm the service `ie-valdivia-portal`.
5. Before the first deploy, set the secret env var:
   - `MONGO_URL` = the MongoDB Atlas connection string from the prerequisites.
   (Other env vars `DB_NAME`, `ADMIN_PASSWORD`, `PYTHON_VERSION`, `NODE_VERSION` are pre-filled by `render.yaml`.)
6. Click **Apply** / **Create Resources**. Render will run `./build.sh` and then start the service.
7. After ~5-7 minutes, Render gives a public URL like `https://ie-valdivia-portal.onrender.com`.
   - Open it. Should load the home page.
   - Go to `Perfil` → `Iniciar Sesión` → role `Administrador`, password `12` → enter portal.
   - Use the floating side buttons to add banners, news, projects, videos, etc. **All changes are saved in MongoDB and visible to every visitor of the URL in real-time (~15s refresh).**
   - Use the amber key icon (top of the floating panel) to change the admin password to something secure.

### Important env vars (set in Render dashboard → Environment)
| Key | Value | Notes |
|-----|-------|-------|
| `MONGO_URL` | `mongodb+srv://USER:PASSWORD@...` | **Required.** From MongoDB Atlas. |
| `DB_NAME` | `ievaldivia` | Any name. Auto-created. |
| `ADMIN_PASSWORD` | `12` | Initial password; admin can change it from the panel. |
| `PYTHON_VERSION` | `3.11.9` | Already in render.yaml. |
| `NODE_VERSION` | `20.11.0` | Already in render.yaml. |

### How it works (single URL)
- Render runs `./build.sh` which:
  1. Installs Python deps from `backend/requirements.txt`.
  2. Installs Node deps and runs `yarn build` inside `frontend/`. This produces `frontend/build/` (the static React app).
- Then Render runs `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`.
- FastAPI serves:
  - `/api/*` → JSON API endpoints
  - `/static/*` → React's static assets
  - any other path → React's `index.html` (SPA routing)

So one URL serves both frontend and backend. The frontend uses relative paths (`/api`) automatically when `REACT_APP_BACKEND_URL` is empty (which is the production default).

### Local development
```bash
# Backend
cd backend
pip install -r requirements.txt
export MONGO_URL="mongodb://localhost:27017"
export DB_NAME="ievaldivia"
uvicorn server:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
yarn install
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
yarn start
```

## Admin usage
- Log in: Perfil → Iniciar Sesión → Rol = Administrador → contraseña = `12` (cámbiala desde el panel después).
- Click any floating button on the right side to open an editor modal.
- All changes are persisted to MongoDB Atlas and visible to all visitors within ~15 seconds.

## Troubleshooting
- **Render build fails on `yarn`**: ensure `NODE_VERSION` env var is `20.11.0` (already in render.yaml).
- **Backend can't connect to MongoDB**: verify `MONGO_URL` value (must include the password) and that Atlas Network Access has `0.0.0.0/0`.
- **Login as admin fails**: default password is `12` unless you changed `ADMIN_PASSWORD` in Render. If you already changed it from the panel, use the new one.
- **Forgot admin password**: in Render dashboard, change `ADMIN_PASSWORD` env var, then go to MongoDB Atlas → Browse Collections → `ievaldivia` → `settings` → delete the doc with `_id: "admin_auth"`. Restart Render service. Default `ADMIN_PASSWORD` will apply again.
