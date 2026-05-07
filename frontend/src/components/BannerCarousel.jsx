import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Image as ImageIcon } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';
import { isYouTube, isVimeo, getEmbedUrl } from '../utils/media';

const BannerMedia = ({ banner }) => {
  if (banner.media_type === 'video' && banner.video_url) {
    if (isYouTube(banner.video_url) || isVimeo(banner.video_url)) {
      const src = getEmbedUrl(banner.video_url) + '?autoplay=1&mute=1&loop=1&playlist=' + (getEmbedUrl(banner.video_url).split('/').pop() || '');
      return (
        <iframe
          src={src}
          title={banner.title || 'banner-video'}
          className="absolute inset-0 w-full h-full"
          frameBorder="0"
          allow="autoplay; encrypted-media; picture-in-picture"
          allowFullScreen
        />
      );
    }
    return (
      <video src={banner.video_url} className="absolute inset-0 w-full h-full object-cover"
             autoPlay muted loop playsInline />
    );
  }
  if (banner.image_url) {
    return <img src={banner.image_url} alt={banner.title || 'banner'} className="absolute inset-0 w-full h-full object-cover" />;
  }
  return <div className="absolute inset-0 bg-gradient-to-br from-blue-900/40 to-slate-900" />;
};

const BannerCarousel = () => {
  const { banners } = useSiteData();
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (banners.length <= 1) return;
    const id = setInterval(() => setIdx((i) => (i + 1) % banners.length), 7000);
    return () => clearInterval(id);
  }, [banners.length]);

  if (banners.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-6 mt-8">
        <div className="iev-card flex flex-col items-center justify-center text-center py-20">
          <div className="w-20 h-20 rounded-2xl bg-amber-100/10 flex items-center justify-center mb-6">
            <ImageIcon className="w-10 h-10 text-amber-400" />
          </div>
          <h3 className="text-xl font-semibold text-white">No hay banners configurados</h3>
          <p className="text-slate-400 mt-2">Los administradores pueden agregar banners desde el botón de edición</p>
        </div>
      </div>
    );
  }

  const b = banners[idx];
  const prev = () => setIdx((i) => (i - 1 + banners.length) % banners.length);
  const next = () => setIdx((i) => (i + 1) % banners.length);

  const Wrapper = ({ children }) => b.link
    ? <a href={b.link} target="_blank" rel="noreferrer" className="block">{children}</a>
    : <div>{children}</div>;

  return (
    <div className="max-w-7xl mx-auto px-6 mt-8">
      <div className="iev-card overflow-hidden relative">
        <Wrapper>
          <div className="relative aspect-[16/6] w-full bg-slate-900">
            <BannerMedia banner={b} />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent pointer-events-none" />
            <div className="absolute bottom-6 left-8 right-8 pointer-events-none">
              {b.title && <h2 className="text-2xl md:text-3xl font-bold text-white">{b.title}</h2>}
              {b.subtitle && <p className="text-slate-200 mt-1 max-w-2xl">{b.subtitle}</p>}
            </div>
          </div>
        </Wrapper>
        {banners.length > 1 && (
          <>
            <button onClick={prev} className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 text-white flex items-center justify-center z-10"><ChevronLeft /></button>
            <button onClick={next} className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 text-white flex items-center justify-center z-10"><ChevronRight /></button>
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
              {banners.map((_, i) => (
                <button key={i} onClick={() => setIdx(i)}
                        className={`w-2.5 h-2.5 rounded-full ${i === idx ? 'bg-white' : 'bg-white/40'}`} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default BannerCarousel;
