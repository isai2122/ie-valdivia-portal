import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';

const empty = { title: '', summary: '', content: '', image_url: '', author: 'Administración', category: 'General', featured: false };

const NewsEditor = ({ open, onClose }) => {
  const { setNews } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/news');
    setItems(data); setNews(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (n) => { setEditing(n.id); setForm({ ...n }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (!form.title || !form.content) { setErr('Título y contenido son obligatorios'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/news', form);
      else await api.put(`/news/${editing}`, form);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar esta noticia?')) return;
    await api.delete(`/news/${id}`);
    await load();
  };

  return (
    <Modal open={open} onClose={onClose} title="Editor de Noticias" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} noticia(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nueva noticia</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <input className="iev-input" placeholder="Título *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input className="iev-input" placeholder="Resumen / lead" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
          <textarea className="iev-input min-h-[150px]" placeholder="Contenido completo *" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
          <input className="iev-input" placeholder="URL imagen" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="iev-input" placeholder="Autor" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
            <input className="iev-input" placeholder="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          </div>
          <label className="flex items-center gap-2 text-slate-200">
            <input type="checkbox" checked={!!form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} />
            Mostrar como destacada en inicio
          </label>
          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300 inline-flex items-center gap-1"><XIcon className="w-4 h-4" /> Cancelar</button>
            <button onClick={save} disabled={saving} className="iev-blue-btn inline-flex items-center gap-1 disabled:opacity-60"><Save className="w-4 h-4" /> {saving ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((n) => (
          <li key={n.id} className="iev-card-soft p-3 flex items-center gap-3">
            {n.image_url ? <img src={n.image_url} alt={n.title} className="w-20 h-14 object-cover rounded-md border border-slate-700" /> : <div className="w-20 h-14 bg-slate-800 rounded-md" />}
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{n.title}</p>
              <p className="text-slate-400 text-xs">{n.category} • {n.author} {n.featured ? '• Destacada' : ''}</p>
            </div>
            <button onClick={() => startEdit(n)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(n.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay noticias</p>}
      </ul>
    </Modal>
  );
};

export default NewsEditor;
