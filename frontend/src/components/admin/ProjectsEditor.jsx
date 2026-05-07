import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';

const empty = { title: '', description: '', long_description: '', image_url: '', tags: [], status: 'En curso', featured: false };

const ProjectsEditor = ({ open, onClose }) => {
  const { setProjects } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [tagsText, setTagsText] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/projects');
    setItems(data); setProjects(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setTagsText(''); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); setTagsText(''); };
  const startEdit = (p) => { setEditing(p.id); setForm({ ...p }); setTagsText((p.tags || []).join(', ')); };
  const cancel = () => { setEditing(null); setForm(empty); setTagsText(''); };

  const save = async () => {
    if (!form.title || !form.description) { setErr('Título y descripción son obligatorios'); return; }
    setSaving(true); setErr('');
    try {
      const payload = { ...form, tags: tagsText.split(',').map((s) => s.trim()).filter(Boolean) };
      if (editing === 'new') await api.post('/projects', payload);
      else await api.put(`/projects/${editing}`, payload);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar este proyecto?')) return;
    await api.delete(`/projects/${id}`);
    await load();
  };

  return (
    <Modal open={open} onClose={onClose} title="Editor de Proyectos" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} proyecto(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nuevo proyecto</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <input className="iev-input" placeholder="Título *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <textarea className="iev-input min-h-[80px]" placeholder="Descripción breve *" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <textarea className="iev-input min-h-[120px]" placeholder="Descripción detallada" value={form.long_description} onChange={(e) => setForm({ ...form, long_description: e.target.value })} />
          <input className="iev-input" placeholder="URL de imagen" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="iev-input" placeholder="Etiquetas (separadas por coma)" value={tagsText} onChange={(e) => setTagsText(e.target.value)} />
            <select className="iev-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option>En curso</option>
              <option>Completado</option>
              <option>Próximamente</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-slate-200">
            <input type="checkbox" checked={!!form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} />
            Mostrar como destacado en inicio
          </label>
          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300 inline-flex items-center gap-1"><XIcon className="w-4 h-4" /> Cancelar</button>
            <button onClick={save} disabled={saving} className="iev-blue-btn inline-flex items-center gap-1 disabled:opacity-60"><Save className="w-4 h-4" /> {saving ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((p) => (
          <li key={p.id} className="iev-card-soft p-3 flex items-center gap-3">
            {p.image_url ? <img src={p.image_url} alt={p.title} className="w-20 h-14 object-cover rounded-md border border-slate-700" /> : <div className="w-20 h-14 bg-slate-800 rounded-md" />}
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{p.title}</p>
              <p className="text-slate-400 text-xs">{p.status}{p.featured ? ' • Destacado' : ''}</p>
            </div>
            <button onClick={() => startEdit(p)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(p.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay proyectos</p>}
      </ul>
    </Modal>
  );
};

export default ProjectsEditor;
