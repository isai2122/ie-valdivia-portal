import React from 'react';
import { Trophy, Star, GraduationCap, Calendar } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';

const AchievementGallery = () => {
  const { achievements } = useSiteData();
  const featuredAchievements = achievements.filter(a => a.featured).slice(0, 6);

  if (featuredAchievements.length === 0) return null;

  return (
    <section className="max-w-7xl mx-auto px-4 md:px-6 mt-16 md:mt-24 mb-12">
      <div className="text-center mb-10">
        <h2 className="text-2xl md:text-4xl font-bold text-white flex items-center justify-center gap-3">
          <Trophy className="w-8 h-8 md:w-10 md:h-10 text-yellow-400 animate-bounce" /> 
          Orgullo Valdiviano
        </h2>
        <p className="text-slate-400 mt-3 max-w-2xl mx-auto">
          Celebrando el talento, la dedicación y los logros de nuestra comunidad estudiantil.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
        {featuredAchievements.map((ach) => (
          <div key={ach.id} className="iev-card group overflow-hidden hover:border-yellow-500/50 transition-all duration-300">
            <div className="relative h-48 md:h-56 overflow-hidden bg-slate-800">
              {ach.image_url ? (
                <img 
                  src={ach.image_url} 
                  alt={ach.title} 
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-900/40 to-indigo-900/40">
                  <GraduationCap className="w-16 h-16 text-blue-300/30" />
                </div>
              )}
              <div className="absolute top-3 right-3">
                <div className="bg-yellow-500 text-black p-1.5 rounded-full shadow-lg">
                  <Star className="w-4 h-4 fill-current" />
                </div>
              </div>
            </div>

            <div className="p-5 md:p-6">
              <div className="flex items-center gap-2 text-yellow-400/90 text-xs font-bold uppercase tracking-widest mb-2">
                <Trophy className="w-3 h-3" /> {ach.title}
              </div>
              <h3 className="text-xl font-bold text-white mb-1">{ach.student_name}</h3>
              {ach.grade && (
                <p className="text-blue-300 text-sm font-medium mb-3 flex items-center gap-1.5">
                  <GraduationCap className="w-4 h-4" /> Grado {ach.grade}
                </p>
              )}
              <p className="text-slate-400 text-sm line-clamp-3 mb-4 italic">
                "{ach.description}"
              </p>
              {ach.date && (
                <div className="flex items-center gap-1.5 text-slate-500 text-xs border-t border-slate-700/50 pt-4">
                  <Calendar className="w-3.5 h-3.5" /> {ach.date}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default AchievementGallery;
