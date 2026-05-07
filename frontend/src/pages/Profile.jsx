import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GraduationCap, KeyRound, Rocket, UserPlus, LogOut, Shield, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Profile = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-12 iev-fadeup text-center">
        <div className="flex justify-center text-6xl mb-4"><GraduationCap className="w-16 h-16 text-blue-300" /></div>
        <h1 className="text-3xl md:text-4xl font-bold text-white">Perfil de Usuario</h1>
        <p className="text-slate-400 mt-3 max-w-xl mx-auto">Accede a tu cuenta para personalizar tu experiencia y acceder a funciones exclusivas</p>

        <div className="iev-card p-6 mt-8 text-left">
          <h3 className="flex items-center gap-2 text-white font-semibold"><KeyRound className="w-5 h-5 text-amber-300" /> Iniciar Sesión</h3>
          <p className="text-slate-400 text-sm mt-2">Inicia sesión para acceder a todas las funcionalidades del portal educativo</p>
          <button onClick={() => navigate('/login')} className="iev-blue-btn w-full mt-5 inline-flex items-center justify-center gap-2">
            <Rocket className="w-4 h-4" /> Iniciar Sesión
          </button>
        </div>
        <div className="iev-card p-6 mt-4 text-left">
          <h3 className="flex items-center gap-2 text-white font-semibold"><UserPlus className="w-5 h-5 text-emerald-300" /> Registrarse</h3>
          <p className="text-slate-400 text-sm mt-2">Crea una cuenta nueva en pocos pasos.</p>
          <Link to="/registro" className="iev-blue-btn w-full mt-5 inline-flex items-center justify-center gap-2">
            <UserPlus className="w-4 h-4" /> Registrarse
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-12 iev-fadeup">
      <div className="iev-card p-8 text-center">
        <div className="w-20 h-20 mx-auto rounded-full bg-blue-600 flex items-center justify-center text-white text-3xl font-bold">
          {user.username?.[0]?.toUpperCase() || 'U'}
        </div>
        <h1 className="text-2xl font-bold text-white mt-4">{user.username}</h1>
        <p className="text-slate-400 mt-1 inline-flex items-center gap-2 justify-center">
          {isAdmin ? <Shield className="w-4 h-4 text-amber-300" /> : <User className="w-4 h-4 text-blue-300" />}
          {isAdmin ? 'Administrador' : 'Visitante'}
        </p>
        <p className="text-slate-300 mt-6 max-w-md mx-auto">
          {isAdmin ? 'Tienes acceso completo al panel administrativo. Usa los botones flotantes a la derecha para editar el contenido del portal.' : 'Disfruta del portal educativo IE Valdivia.'}
        </p>
        <button onClick={logout} className="mt-8 inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-red-400/40 text-red-300 hover:bg-red-500/10">
          <LogOut className="w-4 h-4" /> Cerrar sesión
        </button>
      </div>
    </div>
  );
};

export default Profile;
