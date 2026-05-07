import React, { useState, useEffect } from 'react';
import { Bell, X, Info, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { useSiteData } from '../context/SiteDataContext';

const AnnouncementBar = () => {
  const { announcements } = useSiteData();
  const activeAnnouncements = announcements.filter(a => a.active);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (activeAnnouncements.length > 1) {
      const timer = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % activeAnnouncements.length);
      }, 5000);
      return () => clearInterval(timer);
    }
  }, [activeAnnouncements.length]);

  if (!visible || activeAnnouncements.length === 0) return null;

  const current = activeAnnouncements[currentIndex];

  const styles = {
    info: 'bg-blue-600 text-white',
    warning: 'bg-amber-500 text-black',
    danger: 'bg-red-600 text-white',
    success: 'bg-emerald-600 text-white'
  };

  const Icons = {
    info: Info,
    warning: AlertTriangle,
    danger: AlertCircle,
    success: CheckCircle
  };

  const Icon = Icons[current.type] || Bell;

  return (
    <div className={`relative w-full ${styles[current.type] || styles.info} transition-colors duration-500`}>
      <div className="max-w-7xl mx-auto px-4 py-2 md:py-2.5 flex items-center justify-center gap-3">
        <Icon className="w-4 h-4 md:w-5 md:h-5 shrink-0 animate-pulse" />
        <p className="text-sm md:text-base font-medium text-center">
          {current.text}
          {activeAnnouncements.length > 1 && (
            <span className="ml-2 opacity-70 text-xs hidden md:inline">
              ({currentIndex + 1}/{activeAnnouncements.length})
            </span>
          )}
        </p>
        <button 
          onClick={() => setVisible(false)}
          className="absolute right-2 md:right-4 p-1 hover:bg-black/10 rounded-full transition-colors"
          title="Cerrar avisos"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default AnnouncementBar;
