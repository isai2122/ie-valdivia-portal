import React, { useEffect, useState } from 'react';
import Modal from '../Modal';
import api from '../../api/api';
import { useSiteData } from '../../context/SiteDataContext';

const AboutEditor = ({ open, onClose }) => {
  const { about, setAbout } = useSiteData();
  const [form, setForm] = useState({});
  const [valuesText, setValuesText] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      const a = about || {};
      setForm({ ...a });
      setValuesText((a.values || []).join(', '));
    }
  }, [open, about]);

  const save = async () => {
    setSaving(true);
    try {
      const payload = { ...form, values: valuesText.split(',').map((s) => s.trim()).filter(Boolean) };
      const { data } = await api.put('/about', payload);
      setAbout(data);
      onClose?.();
    } finally { setSaving(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Editar Sobre Nosotros" size="lg">
      <div className="space-y-3">
        <input className="iev-input" placeholder="Título" value={form.title || ''} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <input className="iev-input" placeholder="URL imagen institucional" value={form.image_url || ''} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
        <textarea className="iev-input min-h-[100px]" placeholder="Introducción" value={form.intro || ''} onChange={(e) => setForm({ ...form, intro: e.target.value })} />
        <textarea className="iev-input min-h-[100px]" placeholder="Misión" value={form.mission || ''} onChange={(e) => setForm({ ...form, mission: e.target.value })} />
        <textarea className="iev-input min-h-[100px]" placeholder="Visión" value={form.vision || ''} onChange={(e) => setForm({ ...form, vision: e.target.value })} />
        <textarea className="iev-input min-h-[100px]" placeholder="Historia" value={form.history || ''} onChange={(e) => setForm({ ...form, history: e.target.value })} />
        <input className="iev-input" placeholder="Valores (separados por coma)" value={valuesText} onChange={(e) => setValuesText(e.target.value)} />
        <div className="grid md:grid-cols-3 gap-3">
          <input className="iev-input" placeholder="Dirección" value={form.address || ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <input className="iev-input" placeholder="Teléfono" value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input className="iev-input" placeholder="Email" value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-full border border-slate-600 text-slate-300">Cancelar</button>
          <button onClick={save} disabled={saving} className="iev-blue-btn disabled:opacity-60">{saving ? 'Guardando...' : 'Guardar'}</button>
        </div>
      </div>
    </Modal>
  );
};

export default AboutEditor;
