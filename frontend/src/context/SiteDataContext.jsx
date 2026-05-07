import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from '../api/api';

const SiteDataContext = createContext(null);

export const SiteDataProvider = ({ children }) => {
  const [config, setConfig] = useState({ site_name: 'IE Valdivia', logo_url: '', description: '', footer_text: '' });
  const [banners, setBanners] = useState([]);
  const [news, setNews] = useState([]);
  const [projects, setProjects] = useState([]);
  const [videos, setVideos] = useState([]);
  const [about, setAbout] = useState(null);
  const [social, setSocial] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [c, b, n, p, v, a, s] = await Promise.all([
        api.get('/config'),
        api.get('/banners'),
        api.get('/news'),
        api.get('/projects'),
        api.get('/videos'),
        api.get('/about'),
        api.get('/social'),
      ]);
      setConfig(c.data);
      setBanners(b.data);
      setNews(n.data);
      setProjects(p.data);
      setVideos(v.data);
      setAbout(a.data);
      setSocial(s.data);
    } catch (e) { console.error('refresh err', e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <SiteDataContext.Provider value={{ config, banners, news, projects, videos, about, social, loading, refresh, setConfig, setBanners, setNews, setProjects, setVideos, setAbout, setSocial }}>
      {children}
    </SiteDataContext.Provider>
  );
};

export const useSiteData = () => useContext(SiteDataContext);
