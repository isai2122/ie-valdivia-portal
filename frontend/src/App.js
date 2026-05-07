import React, { useState } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SiteDataProvider } from './context/SiteDataContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import AdminPanel from './components/AdminPanel';
import Home from './pages/Home';
import News from './pages/News';
import NewsDetail from './pages/NewsDetail';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Videos from './pages/Videos';
import About from './pages/About';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register';

function Shell() {
  const [logoOpen, setLogoOpen] = useState(false);
  return (
    <div className="min-h-screen iev-gradient-bg text-slate-100 flex flex-col">
      <Navbar onEditLogo={() => setLogoOpen(true)} />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/noticias" element={<News />} />
          <Route path="/noticias/:id" element={<NewsDetail />} />
          <Route path="/proyectos" element={<Projects />} />
          <Route path="/proyectos/:id" element={<ProjectDetail />} />
          <Route path="/videos" element={<Videos />} />
          <Route path="/sobre-nosotros" element={<About />} />
          <Route path="/perfil" element={<Profile />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Register />} />
        </Routes>
      </main>
      <Footer />
      <AdminPanel logoOpen={logoOpen} setLogoOpen={setLogoOpen} />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SiteDataProvider>
          <Shell />
        </SiteDataProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
