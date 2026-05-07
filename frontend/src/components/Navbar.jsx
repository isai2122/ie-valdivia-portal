import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSiteData } from '../context/SiteDataContext';
import { GraduationCap, Pencil } from 'lucide-react';

const Navbar = ({ onEditLogo }) => {
  const { user, isAdmin } = useAuth();
  const { config } = useSiteData();

  const links = [
    { to: '/', label: 'Inicio', end: true },
    { to: '/noticias', label: 'Noticias' },
    { to: '/proyectos', label: 'Proyectos' },
    { to: '/videos', label: 'Videos' },
    { to: '/sobre-nosotros', label: 'Sobre Nosotros' },
    { to: '/perfil', label: 'Perfil' },
  ];

  const initial = (user?.username?.[0] || 'U').toUpperCase();

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-[rgba(6,8,20,0.7)] border-b border-blue-500/20">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-12 h-12 rounded-full border-2 border-blue-400/60 bg-[#0b1530] flex items-center justify-center overflow-hidden">
            {config.logo_url ? (
              <img src={config.logo_url} alt="logo" className="w-full h-full object-cover" />
            ) : (
              <GraduationCap className="w-6 h-6 text-blue-300" />
            )}
          </div>
          <span className="text-xl font-semibold tracking-wide text-white">{config.site_name || 'IE Valdivia'}</span>
        </Link>

        {isAdmin && (
          <button onClick={onEditLogo} className="hidden md:inline-flex items-center gap-1 text-sm text-blue-300 hover:text-blue-200 ml-2">
            <Pencil className="w-3.5 h-3.5" /> Editar logo
          </button>
        )}

        <nav className="flex items-center gap-2 flex-wrap">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `iev-nav-pill ${isActive ? 'active' : ''}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="w-12 h-12 rounded-full border-2 border-blue-400/60 bg-[#0b1530] flex items-center justify-center text-white font-semibold">
          {initial}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
