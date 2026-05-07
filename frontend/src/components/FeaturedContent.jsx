import React, { useState } from 'react';
import { ClipboardList, Sparkles, Newspaper, FolderKanban, Video as VideoIcon, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSiteData } from '../context/SiteDataContext';
import { isYouTube, isVimeo, getEmbedUrl, getYouTubeThumbnail } from '../utils/media';

const FeaturedContent = () => {
  const { news, projects, videos } = useSiteData();
  const featuredNews = news.filter((n) => n.featured).slice(0, 3);
  const featuredProjects = projects.filter((p) => p.featured).slice(0, 3);
  const featuredVideos = videos.filter((v) => v.featured).slice(0, 3);
  const totalFeatured = featuredNews.length + featuredProjects.length + featuredVideos.length;

  const [activeVideo, setActiveVideo] = useState(null);

  return (
    <section className="max-w-7xl mx-auto px-4 md:px-6 mt-10 md:mt-12">
      <h2 className="text-xl md:text-3xl font-bold text-white text-center flex items-center justify-center gap-2">
        <Sparkles className="w-5 h-5 md:w-6 md:h-6 text-blue-300" /> Contenido Destacado
      </h2>

      {totalFeatured === 0 && (
        <div className="iev-card mt-8 flex flex-col items-center justify-center text-center py-16">
          <div className="w-20 h-20 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6">
            <ClipboardList className="w-10 h-10 text-blue-300" />
          </div>
          <h3 className="text-xl font-semibold text-white">Aún no hay contenido</h3>
          <p className="text-slate-400 mt-2">Sé el primero en crear una publicación</p>
        </div>
      )}

      {featuredNews.length > 0 && (
        <div className="mt-8">
          <h3 className="text-blue-300 font-semibold mb-3 flex items-center gap-2"><Newspaper className="w-4 h-4" /> Noticias destacadas</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5">
            {featuredNews.map((n) => (
              <Link to={`/noticias/${n.id}`} key={n.id} className="iev-card overflow-hidden hover:scale-[1.01] transition-transform">
                {n.image_url && <img src={n.image_url} alt={n.title} className="w-full h-40 object-cover" />}
                <div className="p-4">
                  <span className="inline-block text-xs px-2 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-400/20">{n.category}</span>
                  <h4 className="text-white font-semibold mt-2 line-clamp-2">{n.title}</h4>
                  <p className="text-slate-400 text-sm mt-1 line-clamp-2">{n.summary || n.content}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {featuredVideos.length > 0 && (
        <div className="mt-8">
          <h3 className="text-blue-300 font-semibold mb-3 flex items-center gap-2"><VideoIcon className="w-4 h-4" /> Videos destacados</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5">
            {featuredVideos.map((v) => {
              const thumb = v.thumbnail_url || (isYouTube(v.video_url) ? getYouTubeThumbnail(v.video_url) : '');
              return (
                <button onClick={() => setActiveVideo(v)} key={v.id} className="iev-card overflow-hidden hover:scale-[1.01] transition-transform group text-left">
                  <div className="relative aspect-video bg-slate-900">
                    {thumb && <img src={thumb} alt={v.title} className="absolute inset-0 w-full h-full object-cover" />}
                    <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/40">
                      <div className="w-14 h-14 rounded-full bg-white/95 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                        <Play className="w-6 h-6 text-blue-700 ml-1" />
                      </div>
                    </div>
                  </div>
                  <div className="p-4">
                    <span className="inline-block text-xs px-2 py-1 rounded-full bg-pink-500/15 text-pink-300 border border-pink-400/20">{v.category || 'General'}</span>
                    <h4 className="text-white font-semibold mt-2 line-clamp-2">{v.title}</h4>
                    {v.description && <p className="text-slate-400 text-sm mt-1 line-clamp-2">{v.description}</p>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {featuredProjects.length > 0 && (
        <div className="mt-8">
          <h3 className="text-blue-300 font-semibold mb-3 flex items-center gap-2"><FolderKanban className="w-4 h-4" /> Proyectos destacados</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5">
            {featuredProjects.map((p) => (
              <Link to={`/proyectos/${p.id}`} key={p.id} className="iev-card overflow-hidden hover:scale-[1.01] transition-transform">
                {p.image_url && <img src={p.image_url} alt={p.title} className="w-full h-40 object-cover" />}
                <div className="p-4">
                  <span className="inline-block text-xs px-2 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-400/20">{p.status}</span>
                  <h4 className="text-white font-semibold mt-2 line-clamp-2">{p.title}</h4>
                  <p className="text-slate-400 text-sm mt-1 line-clamp-2">{p.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {activeVideo && (
        <div className="fixed inset-0 z-50 iev-modal-bg flex items-center justify-center p-4" onClick={() => setActiveVideo(null)}>
          <div className="iev-card w-full max-w-4xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-blue-500/20">
              <h3 className="text-white font-semibold">{activeVideo.title}</h3>
              <button onClick={() => setActiveVideo(null)} className="px-3 py-1.5 rounded-full border border-slate-600 text-slate-300 hover:bg-slate-700/40">Cerrar</button>
            </div>
            <div className="aspect-video w-full bg-black">
              {isYouTube(activeVideo.video_url) || isVimeo(activeVideo.video_url) ? (
                <iframe src={getEmbedUrl(activeVideo.video_url) + '?autoplay=1'} title={activeVideo.title}
                        className="w-full h-full" frameBorder="0" allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen />
              ) : (
                <video src={activeVideo.video_url} className="w-full h-full" controls autoPlay />
              )}
            </div>
            {activeVideo.description && <div className="p-4 text-slate-300">{activeVideo.description}</div>}
          </div>
        </div>
      )}
    </section>
  );
};

export default FeaturedContent;
