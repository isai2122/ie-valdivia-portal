import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Video as VideoIcon, Play } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';
import { isYouTube, isVimeo, getEmbedUrl, getYouTubeThumbnail } from '../utils/media';

const VideoCard = ({ v, onPlay }) => {
  const thumb = v.thumbnail_url || (isYouTube(v.video_url) ? getYouTubeThumbnail(v.video_url) : '');
  return (
    <button onClick={() => onPlay(v)} className="iev-card overflow-hidden text-left hover:scale-[1.01] transition-transform group w-full">
      <div className="relative aspect-video bg-slate-900">
        {thumb ? (
          <img src={thumb} alt={v.title} className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-blue-900/40 to-slate-900 flex items-center justify-center">
            <VideoIcon className="w-12 h-12 text-blue-400/50" />
          </div>
        )}
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/40 transition-colors">
          <div className="w-16 h-16 rounded-full bg-white/95 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
            <Play className="w-7 h-7 text-blue-700 ml-1" />
          </div>
        </div>
      </div>
      <div className="p-4">
        <span className="inline-block text-xs px-2 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-400/20">{v.category || 'General'}</span>
        <h3 className="text-white font-semibold mt-2 line-clamp-2">{v.title}</h3>
        {v.description && <p className="text-slate-400 text-sm mt-1 line-clamp-2">{v.description}</p>}
      </div>
    </button>
  );
};

const Videos = () => {
  const { videos } = useSiteData();
  const [active, setActive] = useState(null);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 iev-fadeup">
      <div className="flex items-center gap-3 mb-8">
        <VideoIcon className="w-7 h-7 text-blue-300" />
        <h1 className="text-3xl font-bold text-white">Videos</h1>
      </div>

      {videos.length === 0 ? (
        <div className="iev-card p-16 text-center">
          <p className="text-slate-400">No hay videos publicados aún.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map((v) => <VideoCard key={v.id} v={v} onPlay={setActive} />)}
        </div>
      )}

      {active && (
        <div className="fixed inset-0 z-50 iev-modal-bg flex items-center justify-center p-4" onClick={() => setActive(null)}>
          <div className="iev-card w-full max-w-4xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-blue-500/20">
              <h3 className="text-white font-semibold">{active.title}</h3>
              <button onClick={() => setActive(null)} className="px-3 py-1.5 rounded-full border border-slate-600 text-slate-300 hover:bg-slate-700/40">Cerrar</button>
            </div>
            <div className="aspect-video w-full bg-black">
              {isYouTube(active.video_url) || isVimeo(active.video_url) ? (
                <iframe src={getEmbedUrl(active.video_url) + '?autoplay=1'} title={active.title}
                        className="w-full h-full" frameBorder="0" allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen />
              ) : (
                <video src={active.video_url} className="w-full h-full" controls autoPlay />
              )}
            </div>
            {active.description && <div className="p-4 text-slate-300">{active.description}</div>}
          </div>
        </div>
      )}
    </div>
  );
};

export default Videos;
