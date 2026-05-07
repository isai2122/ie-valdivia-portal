import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon, Image as ImageIcon, Video as VideoIcon } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';
import { isYouTube, isVimeo, getEmbedUrl } from '../../utils/media';

const empty = { title: '', subtitle: '', image_url: '', video_url: '', media_type: 'image', link: '', order: 0 };

const BannerEditor = ({ open, onClose }) => {
  const { setBanners } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/banners');
    setItems(data); setBanners(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (b) => { setEditing(b.id); setForm({ ...empty, ...b }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (form.media_type === 'image' && !form.image_url) { setErr('La URL de la imagen es obligatoria'); return; }
    if (form.media_type === 'video' && !form.video_url) { setErr('La URL del video es obligatoria'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/banners', form);
      else await api.put(`/banners/${editing}`, form);
      await load();
      cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar este banner?')) return;
    await api.delete(`/banners/${id}`);
    await load();
  };

  const isVideoForm = form.media_type === 'video';

  return (
    <Modal open={open} onClose={onClose} title="Editor de Banners" size="lg">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}

      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} banner(s)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nuevo banner</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <div className="flex gap-2">
            <button type="button" onClick={() => setForm({ ...form, media_type: 'image' })}
                    className={`px-4 py-2 rounded-full border inline-flex items-center gap-2 text-sm ${!isVideoForm ? 'bg-blue-600 text-white border-blue-400' : 'border-slate-600 text-slate-300'}`}>
              <ImageIcon className="w-4 h-4" /> Imagen
            </button>
            <button type="button" onClick={() => setForm({ ...form, media_type: 'video' })}
                    className={`px-4 py-2 rounded-full border inline-flex items-center gap-2 text-sm ${isVideoForm ? 'bg-blue-600 text-white border-blue-400' : 'border-slate-600 text-slate-300'}`}>
              <VideoIcon className="w-4 h-4" /> Video
            </button>
          </div>

          <input className="iev-input" placeholder="Título" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input className="iev-input" placeholder="Subtítulo" value={form.subtitle} onChange={(e) => setForm({ ...form, subtitle: e.target.value })} />

          {!isVideoForm ? (
            <>
              <input className="iev-input" placeholder="URL de imagen *" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
              {form.image_url && <img src={form.image_url} alt="prev" className="w-full max-h-48 object-cover rounded-lg" />}
            </>
          ) : (
            <>
              <input className="iev-input" placeholder="URL del video (YouTube / Vimeo / .mp4) *" value={form.video_url} onChange={(e) => setForm({ ...form, video_url: e.target.value })} />
              <p className="text-xs text-slate-400">Soporta YouTube, Vimeo o enlaces directos a archivos .mp4 / .webm</p>
              {form.video_url && (
                <div className="aspect-video w-full rounded-lg overflow-hidden bg-black">
                  {isYouTube(form.video_url) || isVimeo(form.video_url) ? (
                    <iframe src={getEmbedUrl(form.video_url)} title="prev" className="w-full h-full" frameBorder="0" allow="autoplay; encrypted-media" allowFullScreen />
                  ) : (
                    <video src={form.video_url} className="w-full h-full" controls />
                  )}
                </div>
              )}
            </>
          )}

          <input className="iev-input" placeholder="Enlace al hacer clic (opcional)" value={form.link} onChange={(e) => setForm({ ...form, link: e.target.value })} />
          <input className="iev-input" type="number" placeholder="Orden" value={form.order} onChange={(e) => setForm({ ...form, order: parseInt(e.target.value || 0) })} />

          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300 inline-flex items-center gap-1"><XIcon className="w-4 h-4" /> Cancelar</button>
            <button onClick={save} disabled={saving} className="iev-blue-btn inline-flex items-center gap-1 disabled:opacity-60"><Save className="w-4 h-4" /> {saving ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((b) => (
          <li key={b.id} className="iev-card-soft p-3 flex items-center gap-3">
            <div className="w-24 h-16 rounded-md border border-slate-700 overflow-hidden bg-slate-900 flex items-center justify-center flex-shrink-0">
              {b.media_type === 'video' ? <VideoIcon className="w-6 h-6 text-blue-300" /> : (
                b.image_url ? <img src={b.image_url} alt={b.title} className="w-full h-full object-cover" /> : <ImageIcon className="w-6 h-6 text-slate-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{b.title || '(sin título)'}</p>
              <p className="text-slate-400 text-xs truncate">{b.media_type === 'video' ? b.video_url : b.subtitle}</p>
              <p className="text-slate-500 text-xs">Orden: {b.order} • {b.media_type || 'image'}</p>
            </div>
            <button onClick={() => startEdit(b)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(b.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay banners</p>}
      </ul>
    </Modal>
  );
};

export default BannerEditor;
