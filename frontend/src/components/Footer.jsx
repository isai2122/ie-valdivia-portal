import React from 'react';
import { useSiteData } from '../context/SiteDataContext';
import { Globe, Facebook, Instagram, Twitter, Youtube, Send, Music2 } from 'lucide-react';

const iconFor = (platform) => {
  const p = (platform || '').toLowerCase();
  if (p.includes('face')) return Facebook;
  if (p.includes('insta')) return Instagram;
  if (p.includes('twit') || p === 'x') return Twitter;
  if (p.includes('you')) return Youtube;
  if (p.includes('tele')) return Send;
  if (p.includes('tik')) return Music2;
  return Globe;
};

const Footer = () => {
  const { social, config } = useSiteData();
  return (
    <footer className="mt-16 border-t border-blue-500/15">
      <div className="max-w-7xl mx-auto px-6 py-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="flex items-center gap-3">
          <Globe className="w-5 h-5 text-blue-400" />
          <h4 className="text-white font-semibold">Redes Sociales</h4>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {social.length === 0 && (
            <p className="text-sm text-slate-400">No hay redes configuradas</p>
          )}
          {social.map((s) => {
            const Icon = iconFor(s.platform);
            return (
              <a key={s.id} href={s.url} target="_blank" rel="noreferrer"
                 className="w-11 h-11 rounded-full border border-blue-500/30 bg-slate-900/60 flex items-center justify-center text-blue-300 hover:text-white hover:border-blue-400 transition-colors"
                 title={s.label || s.platform}>
                <Icon className="w-5 h-5" />
              </a>
            );
          })}
        </div>
      </div>
      <div className="text-center text-xs text-slate-500 pb-6 space-y-2">
        <p>
          {config.footer_text || `© ${new Date().getFullYear()} ${config.site_name || 'IE Valdivia'} - Portal Educativo`}
        </p>
        <div className="pt-2 border-t border-blue-500/5 max-w-xs mx-auto">
          <p className="text-blue-400/60 font-medium tracking-wide uppercase text-[10px]">
            Desarrollado por
          </p>
          <p className="text-blue-300/80 font-bold text-sm mt-0.5">
            Isai Alexander Ortiz Ortiz
          </p>
          <p className="text-slate-400/70 italic">
            Estudiante de 11-2
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
