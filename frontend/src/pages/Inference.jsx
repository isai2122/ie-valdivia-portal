import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { AlertTriangle, FileUp, Loader2, UploadCloud } from "lucide-react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth/context";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { EmptyState } from "@/components/ui-extra/EmptyState";
import { StatusBadge } from "@/components/ui-extra/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, timeAgo } from "@/lib/format";

export default function Inference() {
  const { user } = useAuth();
  const canUpload = user?.role === "admin" || user?.role === "analyst";

  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState([]);

  const loadJobs = useCallback(() => {
    api.get("/inference/jobs?limit=50").then((r) => setJobs(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    loadJobs();
    const iv = setInterval(loadJobs, 5000); // refresco periódico para ver transiciones de estado
    return () => clearInterval(iv);
  }, [loadJobs]);

  const onDrop = useCallback((accepted) => {
    if (accepted?.[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/x-netcdf": [".nc", ".nc4"], "image/tiff": [".tif", ".tiff"] },
    multiple: false,
    disabled: !canUpload || busy,
  });

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/inference/jobs", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Job ${r.data.job_id} encolado`, { description: r.data.warning });
      setFile(null);
      loadJobs();
    } catch (e) {
      toast.error("No se pudo iniciar la inferencia");
    } finally {
      setBusy(false);
    }
  };

  if (!canUpload) {
    return (
      <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="inference-blocked">
        <PageHeader kicker="IA & Datos" title="Ingesta" />
        <EmptyState
          icon={AlertTriangle}
          title="Rol sin permisos de ingesta"
          description={`Tu rol (${user?.role}) no permite disparar inferencias. Pide acceso a un analista o administrador.`}
          action={<Link to="/alerts" className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400">Ver alertas</Link>}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="inference-page">
      <PageHeader
        kicker="IA & Datos"
        title="Ingesta de datos Sentinel-5P"
        subtitle="Sube un archivo NetCDF (CH₄) para disparar una inferencia del modelo."
      />

      {/* Warning honesto */}
      <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200" data-testid="inference-warning-banner">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">Runner actual: demo-synthetic</div>
            <div className="mt-1 text-amber-300/80">
              El modelo ONNX aún no está cargado. Las detecciones producidas son sintéticas y realistas pero no provienen del modelo real.
            </div>
          </div>
        </div>
      </div>

      {/* Dropzone */}
      <Card className="border-slate-800/80 bg-slate-900/60 p-6" data-testid="inference-dropzone-card">
        <div
          {...getRootProps()}
          className={
            "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed p-10 text-center transition " +
            (isDragActive
              ? "border-emerald-500/60 bg-emerald-500/5"
              : "border-slate-700 bg-slate-950/40 hover:border-emerald-500/30")
          }
          data-testid="inference-dropzone"
        >
          <input {...getInputProps()} data-testid="inference-file-input" />
          <div className="grid h-12 w-12 place-items-center rounded-full bg-emerald-500/10 ring-1 ring-emerald-400/20">
            <UploadCloud className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="mt-4 text-sm text-slate-200">
            {isDragActive
              ? "Suelta el archivo aquí"
              : file ? "Archivo listo para enviar" : "Arrastra un archivo .nc o .tif o haz clic para seleccionarlo"}
          </div>
          <div className="mt-1 text-xs text-slate-500">Máximo 1 archivo · formatos: .nc, .nc4, .tif, .tiff</div>
        </div>

        {file && (
          <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm" data-testid="inference-file-preview">
            <div className="flex min-w-0 items-center gap-3">
              <FileUp className="h-4 w-4 text-emerald-400" />
              <div className="min-w-0">
                <div className="truncate text-slate-200">{file.name}</div>
                <div className="text-[11px] text-slate-500">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline" size="sm"
                onClick={() => setFile(null)}
                className="border-slate-700 bg-slate-900 text-slate-300"
              >
                Quitar
              </Button>
              <Button
                onClick={submit} disabled={busy}
                className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                data-testid="inference-submit-button"
              >
                {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Iniciar inferencia
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Historial */}
      <Card className="mt-6 border-slate-800/80 bg-slate-900/60" data-testid="inference-jobs-card">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h3 className="text-sm font-medium text-slate-200">Jobs recientes</h3>
          <span className="text-[11px] text-slate-500">actualiza cada 5s</span>
        </div>
        {jobs.length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-500">Aún no hay jobs. Sube un archivo arriba.</div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-xs text-slate-500">Job</TableHead>
                  <TableHead className="text-xs text-slate-500">Archivo</TableHead>
                  <TableHead className="text-xs text-slate-500">Estado</TableHead>
                  <TableHead className="text-xs text-slate-500">Detecciones</TableHead>
                  <TableHead className="text-xs text-slate-500">Fecha</TableHead>
                  <TableHead className="text-xs text-slate-500">Runner</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((j) => (
                  <TableRow key={j.id} className="border-slate-800 hover:bg-slate-900/60" data-testid={`job-row-${j.id}`}>
                    <TableCell className="font-mono text-[11px] text-slate-300">{j.id}</TableCell>
                    <TableCell className="text-xs text-slate-300">{j.input_filename}</TableCell>
                    <TableCell><StatusBadge status={j.status} /></TableCell>
                    <TableCell className="text-xs text-slate-300">
                      {j.output_detection_ids?.length || 0}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {formatDateTime(j.created_at)} <span className="ml-1 text-[10px] text-slate-600">· {timeAgo(j.created_at)}</span>
                    </TableCell>
                    <TableCell className="font-mono text-[10px] text-amber-300">{j.runner}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
