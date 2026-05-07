import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon, Trophy } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';

const empty = { title: '', student_name: '', grade: '', description: '', image_url: '', date: '', featured: true };

const AchievementsEditor = ({ open, onClose }) => {
  const { setAchievements } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/achievements');
    setItems(data); setAchievements(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (n) => { setEditing(n.id); setForm({ ...n }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (!form.title || !form.student_name) { setErr('El título y el nombre del estudiante son obligatorios'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/achievements', form);
      else await api.put(`/achievements/${editing}`, form);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar este logro?')) return;
    await api.delete(`/achievements/${id}`);
    await load();
  };

  return (
    <Modal open={open} onClose={onClose} title="Galería de Orgullo Valdiviano" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} logro(s) registrado(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nuevo Logro</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <input className="iev-input" placeholder="Título del Logro (ej: Ganador Olimpiadas) *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="iev-input" placeholder="Nombre del Estudiante *" value={form.student_name} onChange={(e) => setForm({ ...form, student_name: e.target.value })} />
            <input className="iev-input" placeholder="Grado (ej: 11-2)" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
          </div>
          <textarea className="iev-input min-h-[100px]" placeholder="Descripción corta del logro..." value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <input className="iev-input" placeholder="URL de la foto" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="iev-input" placeholder="Fecha (ej: Mayo 2026)" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            <div className="flex items-center pb-1">
              <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
                <input type="checkbox" checked={!!form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} />
                Destacar en galería
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
          <li key={n.id} className="iev-card-soft p-3 flex items-center gap-3">
            {n.image_url ? <img src={n.image_url} alt={n.title} className="w-16 h-16 object-cover rounded-full border-2 border-blue-500/30" /> : 
              <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center border-2 border-blue-500/30">
                <Trophy className="w-8 h-8 text-blue-300" />
              </div>
            }
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{n.title}</p>
              <p className="text-blue-300 text-xs">{n.student_name} {n.grade ? `• ${n.grade}` : ''}</p>
              <p className="text-slate-400 text-[10px] truncate">{n.description}</p>
            </div>
            <button onClick={() => startEdit(n)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center shrink-0"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(n.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center shrink-0"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay logros registrados</p>}
      </ul>
    </Modal>
  );
};

export default AchievementsEditor;
