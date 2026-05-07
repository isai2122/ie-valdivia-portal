import React, { useState } from 'react';
import { Search } from 'lucide-react';
import api from '../api/api';
import { Link } from 'react-router-dom';

const SearchBar = () => {
  const [q, setQ] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e?.preventDefault();
    if (!q.trim()) { setResults(null); return; }
    setLoading(true);
    try {
      const { data } = await api.get('/search', { params: { q } });
      setResults(data);
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 mt-8">
      <form onSubmit={submit} className="iev-card p-2 flex items-center gap-2">
        <Search className="w-5 h-5 text-blue-300 ml-3" />
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Buscar noticias, proyectos o contenido..."
               className="flex-1 bg-transparent outline-none text-slate-100 placeholder-slate-400 px-2" />
        <button type="submit" className="iev-blue-btn">Buscar</button>
      </form>
      {loading && <p className="text-slate-400 text-sm mt-3 px-2">Buscando...</p>}
      {results && (
        <div className="mt-4 iev-card-soft p-4 space-y-3">
          {(results.news?.length || 0) === 0 && (results.projects?.length || 0) === 0 && (results.videos?.length || 0) === 0 && (
            <p className="text-slate-400 text-sm">Sin resultados para “{q}”</p>
          )}
          {results.news?.length > 0 && (
            <div>
              <p className="text-blue-300 text-sm font-semibold mb-2">Noticias</p>
              <ul className="space-y-1">
                {results.news.map((n) => (
                  <li key={n.id}>
                    <Link to={`/noticias/${n.id}`} className="iev-link">{n.title}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {results.videos?.length > 0 && (
            <div>
              <p className="text-blue-300 text-sm font-semibold mb-2">Videos</p>
              <ul className="space-y-1">
                {results.videos.map((v) => (
                  <li key={v.id}>
                    <Link to={`/videos`} className="iev-link">{v.title}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {results.projects?.length > 0 && (
            <div>
              <p className="text-blue-300 text-sm font-semibold mb-2">Proyectos</p>
              <ul className="space-y-1">
                {results.projects.map((p) => (
                  <li key={p.id}>
                    <Link to={`/proyectos/${p.id}`} className="iev-link">{p.title}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
