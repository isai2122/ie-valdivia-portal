import React, { useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { useAuth } from '../../context/AuthContext';
import { KeyRound, Eye, EyeOff } from 'lucide-react';

const PasswordEditor = ({ open, onClose }) => {
  const { user } = useAuth();
  const [current, setCurrent] = useState('');
  const [nextPw, setNextPw] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const reset = () => {
    setCurrent(''); setNextPw(''); setConfirm(''); setMsg(''); setErr('');
  };

  const close = () => { reset(); onClose?.(); };

  const save = async () => {
    setErr(''); setMsg('');
    if (!current) { setErr('Ingresa la contraseña actual'); return; }
    if (!nextPw) { setErr('Ingresa la nueva contraseña'); return; }
    if (nextPw !== confirm) { setErr('La confirmación no coincide'); return; }
    setSaving(true);
    try {
      const { data } = await api.post('/auth/change-password', {
        current_password: current,
        new_password: nextPw,
      });
      if (data?.token) {
        // Update stored token since server rotated it
        localStorage.setItem('iev_token', data.token);
        const stored = JSON.parse(localStorage.getItem('iev_user') || '{}');
        stored.token = data.token;
        localStorage.setItem('iev_user', JSON.stringify(stored));
      }
      setMsg('Contraseña actualizada con éxito');
      setTimeout(() => { close(); }, 1200);
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Error al actualizar la contraseña');
    } finally { setSaving(false); }
  };

  const type = show ? 'text' : 'password';

  return (
    <Modal open={open} onClose={close} title="Cambiar contraseña de administrador">
      <div className="space-y-4">
        <p className="text-slate-400 text-sm">
          Usuario: <span className="text-blue-300 font-semibold">{user?.username || 'admin'}</span>
        </p>

        {err && <div className="p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
        {msg && <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-400/30 text-emerald-200 text-sm">{msg}</div>}

        <div>
          <label className="flex items-center gap-2 text-sm text-slate-200 mb-1">
            <KeyRound className="w-4 h-4 text-amber-300" /> Contraseña actual
          </label>
          <input type={type} className="iev-input" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="Contraseña actual" />
        </div>

        <div>
          <label className="text-sm text-slate-200 mb-1 block">Nueva contraseña</label>
          <input type={type} className="iev-input" value={nextPw} onChange={(e) => setNextPw(e.target.value)} placeholder="Nueva contraseña" />
        </div>

        <div>
          <label className="text-sm text-slate-200 mb-1 block">Confirmar nueva contraseña</label>
          <input type={type} className="iev-input" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repite la nueva contraseña" />
        </div>

        <label className="flex items-center gap-2 text-slate-300 text-sm cursor-pointer select-none">
          <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} />
          {show ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          Mostrar contraseñas
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={close} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300">Cancelar</button>
          <button onClick={save} disabled={saving} className="iev-blue-btn disabled:opacity-60">
            {saving ? 'Guardando...' : 'Actualizar contraseña'}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default PasswordEditor;
