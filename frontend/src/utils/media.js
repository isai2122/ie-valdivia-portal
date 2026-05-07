// Utility helpers for video URL detection and embedding.

export const isYouTube = (url = '') => /youtube\.com|youtu\.be/i.test(url);
export const isVimeo = (url = '') => /vimeo\.com/i.test(url);
export const isDirectVideo = (url = '') => /\.(mp4|webm|ogg|mov)(\?|$)/i.test(url);

export const getYouTubeId = (url = '') => {
  const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([\w-]{6,})/);
  return m ? m[1] : '';
};

export const getVimeoId = (url = '') => {
  const m = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  return m ? m[1] : '';
};

export const getEmbedUrl = (url = '') => {
  if (isYouTube(url)) {
    const id = getYouTubeId(url);
    return id ? `https://www.youtube.com/embed/${id}` : '';
  }
  if (isVimeo(url)) {
    const id = getVimeoId(url);
    return id ? `https://player.vimeo.com/video/${id}` : '';
  }
  return url;
};

export const getYouTubeThumbnail = (url = '') => {
  const id = getYouTubeId(url);
  return id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : '';
};
