import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { Plus, Trash2, Edit3, Save, X as XIcon } from 'lucide-react';
import { useSiteData } from '../../context/SiteDataContext';

const empty = { platform: '', url: '', label: '', order: 0 };

const SocialEditor = ({ open, onClose }) => {
  const { setSocial } = useSiteData();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const load = async () => {
    const { data } = await api.get('/social');
    setItems(data); setSocial(data);
  };
  useEffect(() => { if (open) { load(); setEditing(null); setForm(empty); setErr(''); } }, [open]);

  const startNew = () => { setEditing('new'); setForm(empty); };
  const startEdit = (s) => { setEditing(s.id); setForm({ ...s }); };
  const cancel = () => { setEditing(null); setForm(empty); };

  const save = async () => {
    if (!form.platform || !form.url) { setErr('Plataforma y URL son obligatorias'); return; }
    setSaving(true); setErr('');
    try {
      if (editing === 'new') await api.post('/social', form);
      else await api.put(`/social/${editing}`, form);
      await load(); cancel();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('¿Eliminar esta red?')) return;
    await api.delete(`/social/${id}`);
    await load();
  };

  return (
    <Modal open={open} onClose={onClose} title="Redes Sociales">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-300 text-sm">{items.length} red(es)</p>
        {!editing && <button onClick={startNew} className="iev-blue-btn inline-flex items-center gap-1"><Plus className="w-4 h-4" /> Nueva red</button>}
      </div>

      {editing && (
        <div className="iev-card-soft p-4 mb-4 space-y-3">
          <select className="iev-input" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
            <option value="">Selecciona plataforma...</option>
            <option value="Facebook">Facebook</option>
            <option value="Instagram">Instagram</option>
            <option value="Twitter">Twitter / X</option>
            <option value="YouTube">YouTube</option>
            <option value="TikTok">TikTok</option>
            <option value="Telegram">Telegram</option>
            <option value="WhatsApp">WhatsApp</option>
            <option value="Otro">Otro</option>
          </select>
          <input className="iev-input" placeholder="URL completa *" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <input className="iev-input" placeholder="Etiqueta (opcional)" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
          <input className="iev-input" type="number" placeholder="Orden" value={form.order} onChange={(e) => setForm({ ...form, order: parseInt(e.target.value || 0) })} />
          <div className="flex justify-end gap-2">
            <button onClick={cancel} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300 inline-flex items-center gap-1"><XIcon className="w-4 h-4" /> Cancelar</button>
            <button onClick={save} disabled={saving} className="iev-blue-btn inline-flex items-center gap-1 disabled:opacity-60"><Save className="w-4 h-4" /> {saving ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </div>
      )}

      <ul className="space-y-2">
        {items.map((s) => (
          <li key={s.id} className="iev-card-soft p-3 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium">{s.platform}</p>
              <p className="text-slate-400 text-xs truncate">{s.url}</p>
            </div>
            <button onClick={() => startEdit(s)} className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/40 flex items-center justify-center"><Edit3 className="w-4 h-4" /></button>
            <button onClick={() => remove(s.id)} className="w-9 h-9 rounded-full bg-red-500/20 text-red-200 hover:bg-red-500/40 flex items-center justify-center"><Trash2 className="w-4 h-4" /></button>
          </li>
        ))}
        {items.length === 0 && <p className="text-slate-400 text-sm text-center py-6">No hay redes configuradas</p>}
      </ul>
    </Modal>
  );
};

export default SocialEditor;
