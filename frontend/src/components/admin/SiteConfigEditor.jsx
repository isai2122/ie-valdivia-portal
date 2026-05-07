import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { useSiteData } from '../../context/SiteDataContext';

const SiteConfigEditor = ({ open, onClose }) => {
  const { config, setConfig } = useSiteData();
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (open) setForm({ ...config }); }, [open, config]);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/config', form);
      setConfig(data);
      onClose?.();
    } finally { setSaving(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Configuración del Sitio">
      <div className="space-y-4">
        <div>
          <label className="text-sm text-slate-200 mb-1 block">Nombre del sitio</label>
          <input className="iev-input" value={form.site_name || ''} onChange={(e) => setForm({ ...form, site_name: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-slate-200 mb-1 block">Descripción</label>
          <textarea className="iev-input min-h-[80px]" value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-slate-200 mb-1 block">Texto del pie de página</label>
          <input className="iev-input" value={form.footer_text || ''} onChange={(e) => setForm({ ...form, footer_text: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-slate-200 mb-1 block">URL del logo</label>
          <input className="iev-input" value={form.logo_url || ''} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
        </div>
        <div className="flex justify-end gap-2 pt-3">
          <button onClick={onClose} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300">Cancelar</button>
          <button onClick={save} disabled={saving} className="iev-blue-btn disabled:opacity-60">{saving ? 'Guardando...' : 'Guardar'}</button>
        </div>
      </div>
    </Modal>
  );
};

export default SiteConfigEditor;
