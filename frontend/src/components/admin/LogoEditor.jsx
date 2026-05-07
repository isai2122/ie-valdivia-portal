import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { useSiteData } from '../../context/SiteDataContext';

const LogoEditor = ({ open, onClose }) => {
  const { config, setConfig } = useSiteData();
  const [form, setForm] = useState({ logo_url: '', site_name: '', description: '', footer_text: '' });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => { if (open) setForm({ ...config }); setErr(''); }, [open, config]);

  const save = async () => {
    setSaving(true); setErr('');
    try {
      const { data } = await api.put('/config', form);
      setConfig(data);
      onClose?.();
    } catch (e) { setErr(e?.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Editar Logo y Marca">
      {err && <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-400/30 text-red-200 text-sm">{err}</div>}
      <div className="space-y-4">
        <div>
          <label className="text-sm text-slate-200 mb-1 block">URL del logo (imagen)</label>
          <input className="iev-input" placeholder="https://..." value={form.logo_url || ''} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
          {form.logo_url && (
            <div className="mt-3 flex items-center gap-3">
              <span className="text-xs text-slate-400">Vista previa:</span>
              <img src={form.logo_url} alt="preview" className="w-14 h-14 rounded-full border border-blue-400/40 object-cover" />
            </div>
          )}
        </div>
        <div>
          <label className="text-sm text-slate-200 mb-1 block">Nombre del sitio</label>
          <input className="iev-input" value={form.site_name || ''} onChange={(e) => setForm({ ...form, site_name: e.target.value })} />
        </div>
        <div className="flex justify-end gap-2 pt-3">
          <button onClick={onClose} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300">Cancelar</button>
          <button onClick={save} disabled={saving} className="iev-blue-btn disabled:opacity-60">{saving ? 'Guardando...' : 'Guardar'}</button>
        </div>
      </div>
    </Modal>
  );
};

export default LogoEditor;
