import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import api from '../api/api';

const ProjectDetail = () => {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    setLoading(true);
    api.get(`/projects/${id}`).then((r) => setItem(r.data)).catch(() => setErr('Proyecto no encontrado')).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="max-w-4xl mx-auto px-6 py-10 text-slate-400">Cargando...</div>;
  if (err || !item) return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <p className="text-slate-400">{err}</p>
      <Link to="/proyectos" className="iev-link inline-flex items-center gap-1 mt-4"><ArrowLeft className="w-4 h-4" /> Volver</Link>
    </div>
  );

  return (
    <article className="max-w-4xl mx-auto px-6 py-10 iev-fadeup">
      <Link to="/proyectos" className="iev-link inline-flex items-center gap-1 mb-6"><ArrowLeft className="w-4 h-4" /> Volver a proyectos</Link>
      {item.image_url && <img src={item.image_url} alt={item.title} className="w-full max-h-96 object-cover rounded-2xl mb-6" />}
      <span className="px-2 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-400/20 text-xs">{item.status}</span>
      <h1 className="text-3xl md:text-4xl font-bold text-white mt-3">{item.title}</h1>
      <p className="text-slate-300 text-lg mt-4">{item.description}</p>
      {item.long_description && (
        <div className="text-slate-200 mt-6 leading-relaxed whitespace-pre-wrap">{item.long_description}</div>
      )}
      {item.tags?.length > 0 && (
        <div className="flex gap-2 flex-wrap mt-6">
          {item.tags.map((t) => (
            <span key={t} className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">#{t}</span>
          ))}
        </div>
      )}
    </article>
  );
};

export default ProjectDetail;
