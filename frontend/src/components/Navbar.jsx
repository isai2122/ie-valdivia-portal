import React, { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSiteData } from '../context/SiteDataContext';
import { GraduationCap, Pencil, Menu, X } from 'lucide-react';

const Navbar = ({ onEditLogo }) => {
  const { user, isAdmin } = useAuth();
  const { config } = useSiteData();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

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
    <header className="sticky top-0 z-40 backdrop-blur-md bg-[rgba(6,8,20,0.85)] border-b border-blue-500/20">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-4 md:px-6 py-3">
        <Link to="/" className="flex items-center gap-2 md:gap-3 group shrink-0">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-full border-2 border-blue-400/60 bg-[#0b1530] flex items-center justify-center overflow-hidden shrink-0">
            {config.logo_url ? (
              <img src={config.logo_url} alt="logo" className="w-full h-full object-cover" />
            ) : (
              <GraduationCap className="w-5 h-5 md:w-6 md:h-6 text-blue-300" />
            )}
          </div>
          <span className="text-lg md:text-xl font-semibold tracking-wide text-white truncate max-w-[150px] md:max-w-none">
            {config.site_name || 'IE Valdivia'}
          </span>
        </Link>

        {/* Mobile controls */}
        <div className="flex items-center gap-2 md:hidden">
          <div className="w-9 h-9 rounded-full border border-blue-400/40 bg-[#0b1530] flex items-center justify-center text-white text-sm font-semibold">
            {initial}
          </div>
          <button 
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-10 h-10 flex items-center justify-center text-blue-300 hover:text-white"
          >
            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1 lg:gap-2">
          {isAdmin && (
            <button onClick={onEditLogo} className="inline-flex items-center gap-1 text-xs text-blue-300 hover:text-blue-200 mr-2">
              <Pencil className="w-3 h-3" /> Logo
            </button>
          )}
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `iev-nav-pill ${isActive ? 'active' : ''}`}>
              {l.label}
            </NavLink>
          ))}
          <div className="ml-4 w-10 h-10 rounded-full border-2 border-blue-400/60 bg-[#0b1530] flex items-center justify-center text-white font-semibold">
            {initial}
          </div>
        </nav>
      </div>

      {/* Mobile Menu Overlay */}
      {isMenuOpen && (
        <div className="md:hidden bg-[#060814] border-b border-blue-500/20 py-4 px-6 animate-in fade-in slide-in-from-top-4 duration-200">
          <nav className="flex flex-col gap-3">
            {links.map((l) => (
              <NavLink 
                key={l.to} 
                to={l.to} 
                end={l.end}
                onClick={() => setIsMenuOpen(false)}
                className={({ isActive }) => 
                  `px-4 py-3 rounded-xl border border-blue-500/10 text-center font-medium transition-all ${
                    isActive ? 'bg-blue-600/20 text-blue-300 border-blue-500/40' : 'text-slate-300 bg-slate-900/40'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
            {isAdmin && (
              <button 
                onClick={() => { onEditLogo(); setIsMenuOpen(false); }} 
                className="mt-2 px-4 py-3 rounded-xl border border-dashed border-blue-500/30 text-blue-400 text-sm flex items-center justify-center gap-2"
              >
                <Pencil className="w-4 h-4" /> Editar Logo del Sitio
              </button>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};

export default Navbar;
