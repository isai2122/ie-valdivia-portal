import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useSiteData } from '../context/SiteDataContext';
import { Settings, Image as ImageIcon, Newspaper, FolderKanban, Building2, Globe, Sparkles, LogOut, Video as VideoIcon, KeyRound, Trophy } from 'lucide-react';
import LogoEditor from './admin/LogoEditor';
import BannerEditor from './admin/BannerEditor';
import NewsEditor from './admin/NewsEditor';
import ProjectsEditor from './admin/ProjectsEditor';
import VideosEditor from './admin/VideosEditor';
import AboutEditor from './admin/AboutEditor';
import SocialEditor from './admin/SocialEditor';
import SiteConfigEditor from './admin/SiteConfigEditor';
import PasswordEditor from './admin/PasswordEditor';
import AnnouncementsEditor from './admin/AnnouncementsEditor';
import AchievementsEditor from './admin/AchievementsEditor';

const btnColors = {
  user: 'bg-rose-500',
  password: 'bg-amber-500',
  config: 'bg-red-500',
  banner: 'bg-cyan-500',
  announcements: 'bg-yellow-500',
  achievements: 'bg-indigo-500',
  about: 'bg-orange-500',
  news: 'bg-emerald-500',
  projects: 'bg-purple-500',
  videos: 'bg-pink-500',
  social: 'bg-blue-500',
};

const AdminPanel = ({ logoOpen, setLogoOpen }) => {
  const { isAdmin, logout } = useAuth();
  const { refresh } = useSiteData();
  const [open, setOpen] = useState(null);

  if (!isAdmin) return null;

  const close = () => { setOpen(null); refresh(); };

  return (
    <>
      <div className="fixed right-4 top-1/2 -translate-y-1/2 z-30 flex flex-col gap-3">
        <button onClick={logout} className={`iev-floating ${btnColors.user}`} title="Cerrar sesión">
          <LogOut className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('password')} className={`iev-floating ${btnColors.password}`} title="Cambiar contraseña admin">
          <KeyRound className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('config')} className={`iev-floating ${btnColors.config}`} title="Configuración del sitio">
          <Settings className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('banner')} className={`iev-floating ${btnColors.banner}`} title="Editar banners">
          <ImageIcon className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('announcements')} className={`iev-floating ${btnColors.announcements}`} title="Pizarra Digital (Avisos)">
          <Sparkles className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('achievements')} className={`iev-floating ${btnColors.achievements}`} title="Galería de Orgullo Valdiviano">
          <Trophy className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('about')} className={`iev-floating ${btnColors.about}`} title="Sobre Nosotros">
          <Building2 className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('news')} className={`iev-floating ${btnColors.news}`} title="Editar noticias">
          <Newspaper className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('projects')} className={`iev-floating ${btnColors.projects}`} title="Editar proyectos">
          <FolderKanban className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('videos')} className={`iev-floating ${btnColors.videos}`} title="Editar videos">
          <VideoIcon className="w-5 h-5" />
        </button>
        <button onClick={() => setOpen('social')} className={`iev-floating ${btnColors.social}`} title="Redes sociales">
          <Globe className="w-5 h-5" />
        </button>
      </div>

      <LogoEditor open={logoOpen} onClose={() => { setLogoOpen(false); refresh(); }} />
      <PasswordEditor open={open === 'password'} onClose={close} />
      <SiteConfigEditor open={open === 'config'} onClose={close} />
      <BannerEditor open={open === 'banner'} onClose={close} />
      <NewsEditor open={open === 'news'} onClose={close} />
      <ProjectsEditor open={open === 'projects'} onClose={close} />
      <VideosEditor open={open === 'videos'} onClose={close} />
      <AboutEditor open={open === 'about'} onClose={close} />
      <AnnouncementsEditor open={open === 'announcements'} onClose={close} />
      <AchievementsEditor open={open === 'achievements'} onClose={close} />
      <SocialEditor open={open === 'social'} onClose={close} />
    </>
  );
};

export default AdminPanel;
