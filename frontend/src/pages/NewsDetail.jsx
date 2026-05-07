import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, User } from 'lucide-react';
import api from '../api/api';

const NewsDetail = () => {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    setLoading(true);
    api.get(`/news/${id}`).then((r) => setItem(r.data)).catch(() => setErr('Noticia no encontrada')).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="max-w-4xl mx-auto px-6 py-10 text-slate-400">Cargando...</div>;
  if (err || !item) return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <p className="text-slate-400">{err}</p>
      <Link to="/noticias" className="iev-link inline-flex items-center gap-1 mt-4"><ArrowLeft className="w-4 h-4" /> Volver</Link>
    </div>
  );

  return (
    <article className="max-w-4xl mx-auto px-6 py-10 iev-fadeup">
      <Link to="/noticias" className="iev-link inline-flex items-center gap-1 mb-6"><ArrowLeft className="w-4 h-4" /> Volver a noticias</Link>
      {item.image_url && <img src={item.image_url} alt={item.title} className="w-full max-h-96 object-cover rounded-2xl mb-6" />}
      <span className="px-2 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-400/20 text-xs">{item.category}</span>
      <h1 className="text-3xl md:text-4xl font-bold text-white mt-3">{item.title}</h1>
      <div className="flex items-center gap-4 text-sm text-slate-400 mt-3">
        <span className="flex items-center gap-1"><User className="w-4 h-4" /> {item.author}</span>
        <span className="flex items-center gap-1"><Calendar className="w-4 h-4" /> {new Date(item.created_at).toLocaleDateString('es-CO')}</span>
      </div>
      {item.summary && <p className="text-slate-300 text-lg mt-5 italic">{item.summary}</p>}
      <div className="text-slate-200 mt-6 leading-relaxed whitespace-pre-wrap">{item.content}</div>
    </article>
  );
};

export default NewsDetail;
