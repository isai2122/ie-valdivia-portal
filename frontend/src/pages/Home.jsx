import React from 'react';
import SearchBar from '../components/SearchBar';
import BannerCarousel from '../components/BannerCarousel';
import FeaturedContent from '../components/FeaturedContent';

const Home = () => {
  return (
    <div className="iev-fadeup">
      <SearchBar />
      <BannerCarousel />
      <FeaturedContent />
      <div className="h-16" />
    </div>
  );
};

export default Home;
