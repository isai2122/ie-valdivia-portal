import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Mail, Lock, User } from 'lucide-react';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(''); setMsg('');
    if (!form.username || !form.email || !form.password) { setErr('Todos los campos son obligatorios'); return; }
    setLoading(true);
    try {
      await register(form);
      setMsg('¡Cuenta creada! Ahora puedes iniciar sesión.');
      setTimeout(() => navigate('/login'), 1200);
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Error al registrar');
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-12 iev-fadeup">
      <div className="iev-card p-8">
        <div className="flex justify-center"><UserPlus className="w-14 h-14 text-blue-300" /></div>
        <h1 className="text-2xl font-bold text-white text-center mt-3">Crear Cuenta</h1>

        {err && <div className="mt-5 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
        {msg && <div className="mt-5 p-3 rounded-lg bg-emerald-500/15 border border-emerald-400/30 text-emerald-200 text-sm">{msg}</div>}

        <form onSubmit={submit} className="space-y-4 mt-6">
          <div>
            <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><User className="w-4 h-4 text-blue-300" /> Usuario</label>
            <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="iev-input" />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><Mail className="w-4 h-4 text-blue-300" /> Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="iev-input" />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm text-slate-200 mb-2"><Lock className="w-4 h-4 text-blue-300" /> Contraseña</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="iev-input" />
          </div>
          <button type="submit" disabled={loading} className="iev-blue-btn w-full inline-flex items-center justify-center gap-2 disabled:opacity-60">
            <UserPlus className="w-4 h-4" /> {loading ? 'Creando...' : 'Registrarse'}
          </button>
        </form>
        <p className="text-center text-sm text-slate-400 mt-5">¿Ya tienes cuenta? <Link to="/login" className="iev-link">Inicia sesión</Link></p>
      </div>
    </div>
  );
};

export default Register;
