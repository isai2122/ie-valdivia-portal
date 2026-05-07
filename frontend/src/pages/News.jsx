import React from 'react';
import { Link } from 'react-router-dom';
import { Newspaper, Calendar, User } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';

const News = () => {
  const { news } = useSiteData();

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 iev-fadeup">
      <div className="flex items-center gap-3 mb-8">
        <Newspaper className="w-7 h-7 text-blue-300" />
        <h1 className="text-3xl font-bold text-white">Noticias</h1>
      </div>
      {news.length === 0 ? (
        <div className="iev-card p-16 text-center">
          <p className="text-slate-400">No hay noticias publicadas aún.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {news.map((n) => (
            <Link key={n.id} to={`/noticias/${n.id}`} className="iev-card overflow-hidden hover:scale-[1.01] transition-transform group">
              {n.image_url ? (
                <img src={n.image_url} alt={n.title} className="w-full h-48 object-cover" />
              ) : (
                <div className="w-full h-48 bg-gradient-to-br from-blue-900/40 to-slate-900 flex items-center justify-center">
                  <Newspaper className="w-12 h-12 text-blue-400/40" />
                </div>
              )}
              <div className="p-5">
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-400/20">{n.category}</span>
                  {n.featured && <span className="px-2 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-400/20">Destacada</span>}
                </div>
                <h3 className="text-white font-semibold text-lg mt-3 line-clamp-2 group-hover:text-blue-300">{n.title}</h3>
                <p className="text-slate-400 text-sm mt-2 line-clamp-3">{n.summary || n.content}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500 mt-4">
                  <span className="flex items-center gap-1"><User className="w-3 h-3" /> {n.author}</span>
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(n.created_at).toLocaleDateString('es-CO')}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default News;
