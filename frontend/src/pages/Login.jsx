import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSiteData } from '../context/SiteDataContext';
import { Rocket, Lock, User, School, ShieldCheck } from 'lucide-react';

const Login = () => {
  const { login } = useAuth();
  const { refresh } = useSiteData();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('visitante');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    if (!username.trim()) { setErr('Ingresa un nombre de usuario'); return; }
    if (role === 'admin' && !password) { setErr('La contraseña de administrador es requerida'); return; }
    setLoading(true);
    try {
      await login({ username: username.trim(), role, password });
      await refresh();
      navigate('/');
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || 'Error al iniciar sesión');
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-12 iev-fadeup">
      <div className="iev-card p-8">
        <div className="flex justify-center"><School className="w-14 h-14 text-blue-300" /></div>
        <h1 className="text-2xl font-bold text-white text-center mt-3">Iniciar Sesión</h1>
        <p className="text-slate-400 text-center text-sm mt-1">Portal Educativo IE Valdivia</p>

        {err && <div className="mt-5 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}

        <form onSubmit={submit} className="space-y-4 mt-6">
          <div>
            <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><User className="w-4 h-4 text-blue-300" /> Usuario</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Ingresa tu nombre de usuario" className="iev-input" />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><ShieldCheck className="w-4 h-4 text-blue-300" /> Rol</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="iev-input">
              <option value="visitante">Visitante</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          {role === 'admin' && (
            <div>
              <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><Lock className="w-4 h-4 text-amber-300" /> Contraseña de administrador</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña especial" className="iev-input" />
              <p className="text-xs text-slate-500 mt-1">Contraseña requerida para acceso administrativo</p>
            </div>
          )}
          <button type="submit" disabled={loading} className="iev-blue-btn w-full inline-flex items-center justify-center gap-2 disabled:opacity-60">
            <Rocket className="w-4 h-4" /> {loading ? 'Entrando...' : 'Entrar al Portal'}
          </button>
        </form>
        <p className="text-center text-sm text-slate-400 mt-5">¿Eres nuevo? <Link to="/registro" className="iev-link">Regístrate aquí</Link></p>
      </div>
    </div>
  );
};

export default Login;
