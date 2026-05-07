import React from 'react';
import { useSiteData } from '../context/SiteDataContext';
import { Building2, Target, Eye, History, Heart, MapPin, Phone, Mail } from 'lucide-react';

const About = () => {
  const { about } = useSiteData();
  if (!about) return <div className="max-w-4xl mx-auto px-6 py-10 text-slate-400">Cargando...</div>;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 iev-fadeup">
      <div className="flex items-center gap-3 mb-8">
        <Building2 className="w-7 h-7 text-blue-300" />
        <h1 className="text-3xl font-bold text-white">{about.title || 'Sobre Nosotros'}</h1>
      </div>

      {about.image_url && <img src={about.image_url} alt="about" className="w-full max-h-80 object-cover rounded-2xl mb-8" />}

      {about.intro && (
        <div className="iev-card p-6 mb-6">
          <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">{about.intro}</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {about.mission && (
          <div className="iev-card p-6">
            <h3 className="flex items-center gap-2 text-xl font-semibold text-white"><Target className="w-5 h-5 text-blue-300" /> Misión</h3>
            <p className="text-slate-300 mt-3 leading-relaxed whitespace-pre-wrap">{about.mission}</p>
          </div>
        )}
        {about.vision && (
          <div className="iev-card p-6">
            <h3 className="flex items-center gap-2 text-xl font-semibold text-white"><Eye className="w-5 h-5 text-blue-300" /> Visión</h3>
            <p className="text-slate-300 mt-3 leading-relaxed whitespace-pre-wrap">{about.vision}</p>
          </div>
        )}
      </div>

      {about.history && (
        <div className="iev-card p-6 mt-6">
          <h3 className="flex items-center gap-2 text-xl font-semibold text-white"><History className="w-5 h-5 text-blue-300" /> Historia</h3>
          <p className="text-slate-300 mt-3 leading-relaxed whitespace-pre-wrap">{about.history}</p>
        </div>
      )}

      {about.values?.length > 0 && (
        <div className="iev-card p-6 mt-6">
          <h3 className="flex items-center gap-2 text-xl font-semibold text-white"><Heart className="w-5 h-5 text-blue-300" /> Valores</h3>
          <div className="flex flex-wrap gap-2 mt-4">
            {about.values.map((v, i) => (
              <span key={i} className="px-3 py-1.5 rounded-full bg-blue-500/15 text-blue-200 border border-blue-400/30 text-sm">{v}</span>
            ))}
          </div>
        </div>
      )}

      {(about.address || about.phone || about.email) && (
        <div className="iev-card p-6 mt-6">
          <h3 className="text-xl font-semibold text-white">Contacto</h3>
          <ul className="mt-3 space-y-2 text-slate-300">
            {about.address && <li className="flex items-center gap-2"><MapPin className="w-4 h-4 text-blue-300" /> {about.address}</li>}
            {about.phone && <li className="flex items-center gap-2"><Phone className="w-4 h-4 text-blue-300" /> {about.phone}</li>}
            {about.email && <li className="flex items-center gap-2"><Mail className="w-4 h-4 text-blue-300" /> {about.email}</li>}
          </ul>
        </div>
      )}
    </div>
  );
};

export default About;
