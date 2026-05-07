import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';
import { isYouTube, isVimeo, getEmbedUrl, getYouTubeThumbnail } from '../../utils/media';

const empty = { title: '', description: '', video_url: '', thumbnail_url: '', category: 'General', featured: false, order: 0 };

const VideosEditor = ({ open, onClose }) => {
  const { setVideos } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/videos');
    setItems(data); setVideos(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (v) => { setEditing(v.id); setForm({ ...empty, ...v }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (!form.title || !form.video_url) { setErr('Título y URL del video son obligatorios'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/videos', form);
      else await api.put(`/videos/${editing}`, form);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar este video?')) return;
    await api.delete(`/videos/${id}`);
    await load();
  };

  const previewThumb = form.thumbnail_url || (isYouTube(form.video_url) ? getYouTubeThumbnail(form.video_url) : '');

  return (
    <Modal open={open} onClose={onClose} title="Editor de Videos" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} video(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nuevo video</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <input className="iev-input" placeholder="Título *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <textarea className="iev-input min-h-[80px]" placeholder="Descripción" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <input className="iev-input" placeholder="URL del video (YouTube / Vimeo / .mp4) *" value={form.video_url} onChange={(e) => setForm({ ...form, video_url: e.target.value })} />
          <input className="iev-input" placeholder="URL miniatura (opcional)" value={form.thumbnail_url} onChange={(e) => setForm({ ...form, thumbnail_url: e.target.value })} />
          <p className="text-xs text-slate-400">Si dejas la miniatura vacía y el video es de YouTube, se generará automáticamente.</p>

          {form.video_url && (
            <div className="aspect-video w-full rounded-lg overflow-hidden bg-black">
              {isYouTube(form.video_url) || isVimeo(form.video_url) ? (
                <iframe src={getEmbedUrl(form.video_url)} title="prev" className="w-full h-full" frameBorder="0" allow="autoplay; encrypted-media" allowFullScreen />
              ) : (
                <video src={form.video_url} className="w-full h-full" controls />
              )}
            </div>
          )}
          {previewThumb && <img src={previewThumb} alt="thumb" className="w-32 h-20 object-cover rounded-md border border-slate-700" />}

          <div className="grid grid-cols-2 gap-3">
            <input className="iev-input" placeholder="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <input className="iev-input" type="number" placeholder="Orden" value={form.order} onChange={(e) => setForm({ ...form, order: parseInt(e.target.value || 0) })} />
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
        {items.map((v) => {
          const thumb = v.thumbnail_url || (isYouTube(v.video_url) ? getYouTubeThumbnail(v.video_url) : '');
          return (
            <li key={v.id} className="iev-card-soft p-3 flex items-center gap-3">
              {thumb ? <img src={thumb} alt={v.title} className="w-24 h-16 object-cover rounded-md border border-slate-700" /> : <div className="w-24 h-16 bg-slate-800 rounded-md" />}
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium truncate">{v.title}</p>
                <p className="text-slate-400 text-xs truncate">{v.video_url}</p>
                <p className="text-slate-500 text-xs">{v.category}{v.featured ? ' • Destacado' : ''}</p>
              </div>
              <button onClick={() => startEdit(v)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center"><Edit3 className="w-4 h-4" /></button>
              <button onClick={() => remove(v.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center"><Trash2 className="w-4 h-4" /></button>
            </li>
          );
        })}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay videos</p>}
      </ul>
    </Modal>
  );
};

export default VideosEditor;
