import React from 'react';
import { Link } from 'react-router-dom';
import { FolderKanban } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';

const statusColor = (s) => {
  if (s === 'Completado') return 'bg-emerald-500/15 text-emerald-300 border-emerald-400/20';
  if (s === 'Próximamente') return 'bg-amber-500/15 text-amber-300 border-amber-400/20';
  return 'bg-blue-500/15 text-blue-300 border-blue-400/20';
};

const Projects = () => {
  const { projects } = useSiteData();
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 iev-fadeup">
      <div className="flex items-center gap-3 mb-8">
        <FolderKanban className="w-7 h-7 text-blue-300" />
        <h1 className="text-3xl font-bold text-white">Proyectos</h1>
      </div>
      {projects.length === 0 ? (
        <div className="iev-card p-16 text-center"><p className="text-slate-400">No hay proyectos publicados.</p></div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((p) => (
            <Link key={p.id} to={`/proyectos/${p.id}`} className="iev-card overflow-hidden hover:scale-[1.01] transition-transform group">
              {p.image_url ? (
                <img src={p.image_url} alt={p.title} className="w-full h-48 object-cover" />
              ) : (
                <div className="w-full h-48 bg-gradient-to-br from-blue-900/40 to-slate-900 flex items-center justify-center">
                  <FolderKanban className="w-12 h-12 text-blue-400/40" />
                </div>
              )}
              <div className="p-5">
                <span className={`inline-block text-xs px-2 py-1 rounded-full border ${statusColor(p.status)}`}>{p.status}</span>
                <h3 className="text-white font-semibold text-lg mt-3 line-clamp-2 group-hover:text-blue-300">{p.title}</h3>
                <p className="text-slate-400 text-sm mt-2 line-clamp-3">{p.description}</p>
                {p.tags?.length > 0 && (
                  <div className="flex gap-1.5 flex-wrap mt-3">
                    {p.tags.slice(0, 4).map((t) => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">#{t}</span>
                    ))}
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default Projects;
