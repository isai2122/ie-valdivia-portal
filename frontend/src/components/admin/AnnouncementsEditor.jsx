import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon, Bell } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';

const empty = { text: '', type: 'info', active: true };

const AnnouncementsEditor = ({ open, onClose }) => {
  const { setAnnouncements } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/announcements');
    setItems(data); setAnnouncements(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (n) => { setEditing(n.id); setForm({ ...n }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (!form.text) { setErr('El texto del aviso es obligatorio'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/announcements', form);
      else await api.put(`/announcements/${editing}`, form);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar este aviso?')) return;
    await api.delete(`/announcements/${id}`);
    await load();
  };

  return (
    <Modal open={open} onClose={onClose} title="Pizarra Digital (Avisos Urgentes)" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} aviso(s) configurado(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nuevo aviso</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <textarea className="iev-input min-h-[80px]" placeholder="Texto del aviso (máx 150 caracteres sugerido) *" value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1 ml-2">Tipo de aviso</label>
              <select className="iev-input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="info">Información (Azul)</option>
                <option value="warning">Alerta (Amarillo)</option>
                <option value="danger">Urgente (Rojo)</option>
                <option value="success">Éxito (Verde)</option>
              </select>
            </div>
            <div className="flex items-end pb-3">
              <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
                <input type="checkbox" checked={!!form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
                Aviso activo
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300 inline-flex items-center gap-1"><XIcon className="w-4 h-4" /> Cancelar</button>
            <button onClick={save} disabled={saving} className="iev-blue-btn inline-flex items-center gap-1 disabled:opacity-60"><Save className="w-4 h-4" /> {saving ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((n) => (
          <li key={n.id} className={`iev-card-soft p-3 flex items-center gap-3 ${!n.active ? 'opacity-50' : ''}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
              n.type === 'danger' ? 'bg-red-500/20 text-red-400' : 
              n.type === 'warning' ? 'bg-amber-500/20 text-amber-400' : 
              n.type === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 
              'bg-blue-500/20 text-blue-400'
            }`}>
              <Bell className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium text-sm line-clamp-2">{n.text}</p>
              <p className="text-slate-400 text-[10px] uppercase tracking-wider">{n.type} {n.active ? '• ACTIVO' : '• INACTIVO'}</p>
            </div>
            <button onClick={() => startEdit(n)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center shrink-0"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(n.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center shrink-0"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay avisos configurados</p>}
      </ul>
    </Modal>
  );
};

export default AnnouncementsEditor;
