from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import secrets
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL') or os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'ievaldivia')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="IE Valdivia Portal")
api_router = APIRouter(prefix="/api")

# Default admin password (can be overridden by env var or DB)
DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '12')


async def get_admin_password() -> str:
    """Get current admin password from DB, falling back to env default."""
    doc = await db.settings.find_one({"_id": "admin_auth"})
    if doc and doc.get("password"):
        return doc["password"]
    return DEFAULT_ADMIN_PASSWORD


async def get_admin_token() -> str:
    """Get or create a stable admin token stored in DB."""
    doc = await db.settings.find_one({"_id": "admin_auth"})
    if doc and doc.get("token"):
        return doc["token"]
    token = secrets.token_urlsafe(32)
    await db.settings.update_one(
        {"_id": "admin_auth"},
        {"$setOnInsert": {"password": DEFAULT_ADMIN_PASSWORD}, "$set": {"token": token}},
        upsert=True,
    )
    return token


# ============= MODELS =============
class LoginRequest(BaseModel):
    username: str
    role: str  # 'visitante' or 'admin'
    password: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: str
    role: str
    message: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


# Site config (logo, name)
class SiteConfig(BaseModel):
    site_name: str = "IE Valdivia"
    logo_url: str = ""
    description: str = "Portal Educativo IE Valdivia"
    footer_text: str = "© 2025 IE Valdivia - Portal Educativo"


# Banner
class Banner(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    subtitle: str = ""
    image_url: str = ""
    video_url: str = ""  # mp4 / YouTube / Vimeo
    media_type: str = "image"  # 'image' or 'video'
    link: str = ""
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BannerCreate(BaseModel):
    title: str = ""
    subtitle: str = ""
    image_url: str = ""
    video_url: str = ""
    media_type: str = "image"
    link: str = ""
    order: int = 0


# News
class News(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    summary: str = ""
    content: str
    image_url: str = ""
    author: str = "Administración"
    category: str = "General"
    featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NewsCreate(BaseModel):
    title: str
    summary: str = ""
    content: str
    image_url: str = ""
    author: str = "Administración"
    category: str = "General"
    featured: bool = False


# Project
class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    long_description: str = ""
    image_url: str = ""
    tags: List[str] = []
    status: str = "En curso"  # En curso, Completado, Próximamente
    featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(BaseModel):
    title: str
    description: str
    long_description: str = ""
    image_url: str = ""
    tags: List[str] = []
    status: str = "En curso"
    featured: bool = False


# About Us
class AboutUs(BaseModel):
    title: str = "Sobre Nosotros"
    intro: str = ""
    mission: str = ""
    vision: str = ""
    history: str = ""
    values: List[str] = []
    image_url: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""


# Social Media
class SocialLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str  # facebook, instagram, twitter, youtube, tiktok, etc
    url: str
    label: str = ""
    order: int = 0


class SocialLinkCreate(BaseModel):
    platform: str
    url: str
    label: str = ""
    order: int = 0


# Video
class Video(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    video_url: str  # YouTube, Vimeo, or direct mp4 URL
    thumbnail_url: str = ""
    category: str = "General"
    featured: bool = False
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoCreate(BaseModel):
    title: str
    description: str = ""
    video_url: str
    thumbnail_url: str = ""
    category: str = "General"
    featured: bool = False
    order: int = 0


# ============= AUTH =============
async def verify_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    token = authorization.replace("Bearer ", "")
    current_token = await get_admin_token()
    if token != current_token:
        raise HTTPException(status_code=401, detail="Token inválido")
    return True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@api_router.get("/")
async def root():
    return {"message": "IE Valdivia Portal API"}


@api_router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if req.role == "admin":
        admin_pw = await get_admin_password()
        if not req.password or req.password != admin_pw:
            return LoginResponse(success=False, username=req.username, role=req.role,
                                  message="Contraseña incorrecta")
        token = await get_admin_token()
        return LoginResponse(success=True, token=token, username=req.username or "admin",
                              role="admin", message="Bienvenido administrador")
    # visitante
    return LoginResponse(success=True, token="visitor", username=req.username or "Visitante",
                          role="visitante", message="Bienvenido al portal")


@api_router.post("/auth/change-password")
async def change_admin_password(req: ChangePasswordRequest, _admin: bool = Depends(verify_admin)):
    current_pw = await get_admin_password()
    if req.current_password != current_pw:
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if not req.new_password or len(req.new_password) < 1:
        raise HTTPException(status_code=400, detail="La nueva contraseña no puede estar vacía")
    # Rotate token so old sessions are invalidated
    new_token = secrets.token_urlsafe(32)
    await db.settings.update_one(
        {"_id": "admin_auth"},
        {"$set": {"password": req.new_password, "token": new_token}},
        upsert=True,
    )
    return {"success": True, "message": "Contraseña actualizada", "token": new_token}


@api_router.post("/auth/register")
async def register(req: RegisterRequest):
    # Mock register: store in users collection
    existing = await db.users.find_one({"username": req.username})
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    user = {
        "id": str(uuid.uuid4()),
        "username": req.username,
        "email": req.email,
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.users.insert_one(user)
    return {"success": True, "message": "Usuario registrado", "username": req.username}


# ============= SITE CONFIG =============
@api_router.get("/config", response_model=SiteConfig)
async def get_config():
    cfg = await db.site_config.find_one({"_id": "main"})
    if not cfg:
        default = SiteConfig().model_dump()
        await db.site_config.insert_one({"_id": "main", **default})
        return SiteConfig(**default)
    cfg.pop("_id", None)
    return SiteConfig(**cfg)


@api_router.put("/config", response_model=SiteConfig)
async def update_config(cfg: SiteConfig, _admin: bool = Depends(verify_admin)):
    data = cfg.model_dump()
    await db.site_config.update_one({"_id": "main"}, {"$set": data}, upsert=True)
    return cfg


# ============= BANNERS =============
@api_router.get("/banners", response_model=List[Banner])
async def get_banners():
    items = await db.banners.find().sort("order", 1).to_list(100)
    for it in items:
        it.pop("_id", None)
    return [Banner(**i) for i in items]


@api_router.post("/banners", response_model=Banner)
async def create_banner(banner: BannerCreate, _admin: bool = Depends(verify_admin)):
    obj = Banner(**banner.model_dump())
    await db.banners.insert_one(obj.model_dump())
    return obj


@api_router.put("/banners/{banner_id}", response_model=Banner)
async def update_banner(banner_id: str, banner: BannerCreate, _admin: bool = Depends(verify_admin)):
    existing = await db.banners.find_one({"id": banner_id})
    if not existing:
        raise HTTPException(404, "Banner no encontrado")
    data = banner.model_dump()
    await db.banners.update_one({"id": banner_id}, {"$set": data})
    existing.update(data)
    existing.pop("_id", None)
    return Banner(**existing)


@api_router.delete("/banners/{banner_id}")
async def delete_banner(banner_id: str, _admin: bool = Depends(verify_admin)):
    res = await db.banners.delete_one({"id": banner_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Banner no encontrado")
    return {"success": True}


# ============= NEWS =============
@api_router.get("/news", response_model=List[News])
async def get_news():
    items = await db.news.find().sort("created_at", -1).to_list(500)
    for it in items:
        it.pop("_id", None)
    return [News(**i) for i in items]


@api_router.get("/news/{news_id}", response_model=News)
async def get_news_one(news_id: str):
    item = await db.news.find_one({"id": news_id})
    if not item:
        raise HTTPException(404, "Noticia no encontrada")
    item.pop("_id", None)
    return News(**item)


@api_router.post("/news", response_model=News)
async def create_news(news: NewsCreate, _admin: bool = Depends(verify_admin)):
    obj = News(**news.model_dump())
    await db.news.insert_one(obj.model_dump())
    return obj


@api_router.put("/news/{news_id}", response_model=News)
async def update_news(news_id: str, news: NewsCreate, _admin: bool = Depends(verify_admin)):
    existing = await db.news.find_one({"id": news_id})
    if not existing:
        raise HTTPException(404, "Noticia no encontrada")
    data = news.model_dump()
    data["updated_at"] = datetime.utcnow()
    await db.news.update_one({"id": news_id}, {"$set": data})
    existing.update(data)
    existing.pop("_id", None)
    return News(**existing)


@api_router.delete("/news/{news_id}")
async def delete_news(news_id: str, _admin: bool = Depends(verify_admin)):
    res = await db.news.delete_one({"id": news_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Noticia no encontrada")
    return {"success": True}


# ============= PROJECTS =============
@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    items = await db.projects.find().sort("created_at", -1).to_list(500)
    for it in items:
        it.pop("_id", None)
    return [Project(**i) for i in items]


@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project_one(project_id: str):
    item = await db.projects.find_one({"id": project_id})
    if not item:
        raise HTTPException(404, "Proyecto no encontrado")
    item.pop("_id", None)
    return Project(**item)


@api_router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate, _admin: bool = Depends(verify_admin)):
    obj = Project(**project.model_dump())
    await db.projects.insert_one(obj.model_dump())
    return obj


@api_router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, project: ProjectCreate, _admin: bool = Depends(verify_admin)):
    existing = await db.projects.find_one({"id": project_id})
    if not existing:
        raise HTTPException(404, "Proyecto no encontrado")
    data = project.model_dump()
    await db.projects.update_one({"id": project_id}, {"$set": data})
    existing.update(data)
    existing.pop("_id", None)
    return Project(**existing)


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str, _admin: bool = Depends(verify_admin)):
    res = await db.projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Proyecto no encontrado")
    return {"success": True}


# ============= ABOUT US =============
@api_router.get("/about", response_model=AboutUs)
async def get_about():
    item = await db.about.find_one({"_id": "main"})
    if not item:
        default = AboutUs().model_dump()
        await db.about.insert_one({"_id": "main", **default})
        return AboutUs(**default)
    item.pop("_id", None)
    return AboutUs(**item)


@api_router.put("/about", response_model=AboutUs)
async def update_about(about: AboutUs, _admin: bool = Depends(verify_admin)):
    data = about.model_dump()
    await db.about.update_one({"_id": "main"}, {"$set": data}, upsert=True)
    return about


# ============= SOCIAL =============
@api_router.get("/social", response_model=List[SocialLink])
async def get_social():
    items = await db.social.find().sort("order", 1).to_list(100)
    for it in items:
        it.pop("_id", None)
    return [SocialLink(**i) for i in items]


@api_router.post("/social", response_model=SocialLink)
async def create_social(s: SocialLinkCreate, _admin: bool = Depends(verify_admin)):
    obj = SocialLink(**s.model_dump())
    await db.social.insert_one(obj.model_dump())
    return obj


@api_router.put("/social/{sid}", response_model=SocialLink)
async def update_social(sid: str, s: SocialLinkCreate, _admin: bool = Depends(verify_admin)):
    existing = await db.social.find_one({"id": sid})
    if not existing:
        raise HTTPException(404, "Red social no encontrada")
    data = s.model_dump()
    await db.social.update_one({"id": sid}, {"$set": data})
    existing.update(data)
    existing.pop("_id", None)
    return SocialLink(**existing)


@api_router.delete("/social/{sid}")
async def delete_social(sid: str, _admin: bool = Depends(verify_admin)):
    res = await db.social.delete_one({"id": sid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Red no encontrada")
    return {"success": True}


# ============= VIDEOS =============
@api_router.get("/videos", response_model=List[Video])
async def get_videos():
    items = await db.videos.find().sort("order", 1).to_list(500)
    for it in items:
        it.pop("_id", None)
    return [Video(**i) for i in items]


@api_router.get("/videos/{vid}", response_model=Video)
async def get_video_one(vid: str):
    item = await db.videos.find_one({"id": vid})
    if not item:
        raise HTTPException(404, "Video no encontrado")
    item.pop("_id", None)
    return Video(**item)


@api_router.post("/videos", response_model=Video)
async def create_video(v: VideoCreate, _admin: bool = Depends(verify_admin)):
    obj = Video(**v.model_dump())
    await db.videos.insert_one(obj.model_dump())
    return obj


@api_router.put("/videos/{vid}", response_model=Video)
async def update_video(vid: str, v: VideoCreate, _admin: bool = Depends(verify_admin)):
    existing = await db.videos.find_one({"id": vid})
    if not existing:
        raise HTTPException(404, "Video no encontrado")
    data = v.model_dump()
    await db.videos.update_one({"id": vid}, {"$set": data})
    existing.update(data)
    existing.pop("_id", None)
    return Video(**existing)


@api_router.delete("/videos/{vid}")
async def delete_video(vid: str, _admin: bool = Depends(verify_admin)):
    res = await db.videos.delete_one({"id": vid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Video no encontrado")
    return {"success": True}


# ============= SEARCH =============
@api_router.get("/search")
async def search(q: str = ""):
    if not q or len(q) < 2:
        return {"news": [], "projects": [], "videos": []}
    regex = {"$regex": q, "$options": "i"}
    news_items = await db.news.find({"$or": [{"title": regex}, {"content": regex}, {"summary": regex}]}).limit(20).to_list(20)
    proj_items = await db.projects.find({"$or": [{"title": regex}, {"description": regex}]}).limit(20).to_list(20)
    video_items = await db.videos.find({"$or": [{"title": regex}, {"description": regex}]}).limit(20).to_list(20)
    for it in news_items:
        it.pop("_id", None)
    for it in proj_items:
        it.pop("_id", None)
    for it in video_items:
        it.pop("_id", None)
    return {"news": news_items, "projects": proj_items, "videos": video_items}


app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Portal IE Valdivia arrancando en el puerto {port}")
    try:
        await db.command("ping")
        logger.info("Conexión exitosa a MongoDB Atlas")
    except Exception as e:
        logger.error(f"Error conectando a MongoDB: {e}")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Serve React frontend build (for production single-URL deployment like Render)
FRONTEND_BUILD = ROOT_DIR.parent / "frontend" / "build"
if FRONTEND_BUILD.exists():
    # Static assets (JS, CSS, images)
    static_dir = FRONTEND_BUILD / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Never catch /api paths (handled by api_router)
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        # Serve concrete files if they exist in build folder
        requested = FRONTEND_BUILD / full_path
        if full_path and requested.is_file():
            return FileResponse(requested)
        # Otherwise, serve React index.html (SPA routing)
        index_file = FRONTEND_BUILD / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build not found")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
