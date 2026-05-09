/**
 * Model.jsx — Estado del modelo MetanoSRGAN Elite v5.0
 * Datos reales via tRPC: arquitectura, métricas, pipeline
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle, CheckCircle, Cpu, Database, Play,
  Satellite, Sparkles, Zap,
} from "lucide-react";

import { trpc } from "@/lib/trpc";
import { useQuery, useMutation } from "@/hooks/useTRPC";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function KV({ k, v, mono, highlight }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-800/60 py-2.5 text-sm">
      <span className="text-xs uppercase tracking-wider text-slate-500">{k}</span>
      <span className={
        "text-right " +
        (mono ? "font-mono text-xs " : "") +
        (highlight ? "text-emerald-400 font-semibold " : "text-slate-200 ")
      }>
        {v}
      </span>
    </div>
  );
}

const ARCH_LAYERS = [
  { name: "Entrada", desc: "Sentinel-5P TROPOMI 7km", color: "#38bdf8" },
  { name: "RRDB Encoder", desc: "Residual Dense Blocks (23 bloques)", color: "#818cf8" },
  { name: "Swin Transformer", desc: "Window Attention 8×8, 6 capas", color: "#a78bfa" },
  { name: "Diffusion Refiner", desc: "DDPM 1000 pasos, β schedule coseno", color: "#c084fc" },
  { name: "Salida SR", desc: "Super-resolución 10m + detecciones", color: "#10b981" },
];

export default function Model() {
  const [pipelineResult, setPipelineResult] = useState(null);

  // ── tRPC Queries ──────────────────────────────────────────────────────────
  const { data: modelInfo, loading } = useQuery(
    () => trpc.model.status(),
    []
  );

  const { data: stats } = useQuery(() => trpc.stats.overview(), []);

  const { mutate: runPipeline, loading: pipelineLoading } = useMutation(
    (body) => trpc.pipeline.run(body),
    {
      onSuccess: (result) => {
        setPipelineResult(result);
        toast.success(`Pipeline encolado: ${result.job_id}`);
      },
      onError: () => toast.error("Error al iniciar el pipeline"),
    }
  );

  const psnrPct = modelInfo ? Math.min(100, (modelInfo.psnr_db / 45) * 100) : 0;

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="model-page">
      <PageHeader
        kicker="Motor IA · v5.0"
        title="MetanoSRGAN Elite v2.1"
        subtitle="Arquitectura híbrida RRDB + Swin Transformer + Diffusion Refiner. PSNR 32.19 dB sobre datos sintéticos."
      />

      {/* Banner estado ONNX */}
      <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-medium">Exportación ONNX pendiente</div>
            <div className="mt-1 text-amber-300/80">
              El checkpoint <code className="rounded bg-slate-900 px-1 font-mono text-xs">best.pt</code> está
              disponible en Google Drive. Ejecutar celda [13] del notebook v2.1 para generar{" "}
              <code className="rounded bg-slate-900 px-1 font-mono text-xs">metano_srgan_elite.onnx</code>{" "}
              e integrar inferencia real en producción.
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* ── Info del modelo ── */}
        <Card className="border-slate-800/80 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-medium text-slate-200">Estado del modelo</h3>
            {modelInfo && (
              <Badge variant="outline" className="ml-auto border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-[10px]">
                <CheckCircle className="mr-1 h-3 w-3" />
                {modelInfo.training_status === "completed" ? "Entrenado" : "En progreso"}
              </Badge>
            )}
          </div>

          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-8 bg-slate-900/80" />
              ))}
            </div>
          ) : modelInfo ? (
            <div>
              <KV k="Nombre" v={modelInfo.name} />
              <KV k="Versión" v={modelInfo.version} />
              <KV k="Arquitectura" v={modelInfo.architecture} />
              <KV k="PSNR (mejor)" v={`${modelInfo.psnr_db} dB`} highlight mono />
              <KV k="Épocas entrenadas" v={modelInfo.epochs_trained} mono />
              <KV k="Checkpoint" v={modelInfo.best_checkpoint} mono />
              <KV k="Resolución entrada" v={modelInfo.input_resolution} />
              <KV k="Resolución salida" v={modelInfo.output_resolution} />
              <KV k="Región" v={modelInfo.region} />
              <KV k="Fuente datos" v={modelInfo.data_source} />
              <KV k="Último entrenamiento" v={modelInfo.last_trained?.slice(0, 10)} mono />
              <KV k="Estado ONNX" v={modelInfo.onnx_status === "pending_export" ? "Pendiente exportación" : "Listo"} />

              {/* PSNR Progress */}
              <div className="mt-4">
                <div className="mb-1.5 flex items-center justify-between text-xs">
                  <span className="text-slate-400">PSNR relativo (objetivo 45 dB)</span>
                  <span className="font-mono text-emerald-400">{modelInfo.psnr_db} dB</span>
                </div>
                <Progress value={psnrPct} className="h-2 bg-slate-800" />
                <div className="mt-1 text-[10px] text-slate-500">
                  {psnrPct.toFixed(0)}% del objetivo de producción (45 dB)
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">No se pudo cargar la información del modelo.</div>
          )}
        </Card>

        {/* ── Pipeline Control ── */}
        <div className="space-y-4">
          <Card className="border-slate-800/80 bg-slate-900/60 p-5">
            <div className="mb-3 flex items-center gap-2">
              <Play className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-medium text-slate-200">Control del pipeline</h3>
            </div>
            <p className="mb-4 text-xs text-slate-400">
              Dispara el pipeline de detección sobre los datos más recientes de Sentinel-5P.
            </p>
            <Button
              onClick={() => runPipeline({ force_refresh: true })}
              disabled={pipelineLoading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs"
            >
              {pipelineLoading ? (
                <>
                  <Zap className="mr-2 h-3.5 w-3.5 animate-pulse" />
                  Iniciando...
                </>
              ) : (
                <>
                  <Satellite className="mr-2 h-3.5 w-3.5" />
                  Ejecutar pipeline
                </>
              )}
            </Button>

            {pipelineResult && (
              <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs">
                <div className="font-medium text-emerald-400">{pipelineResult.message}</div>
                <div className="mt-1 font-mono text-slate-400">{pipelineResult.job_id}</div>
                <div className="mt-1 text-slate-500">
                  ETA: ~{pipelineResult.estimated_duration_s}s
                </div>
              </div>
            )}
          </Card>

          {/* Stats del sistema */}
          <Card className="border-slate-800/80 bg-slate-900/60 p-5">
            <div className="mb-3 flex items-center gap-2">
              <Database className="h-4 w-4 text-sky-400" />
              <h3 className="text-sm font-medium text-slate-200">Datos procesados</h3>
            </div>
            {stats ? (
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Total detecciones</dt>
                  <dd className="font-mono text-slate-200">{stats.total_detections}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">PPB promedio</dt>
                  <dd className="font-mono text-emerald-400">{stats.avg_ppb?.toFixed(1)} ppb</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">PPB máximo</dt>
                  <dd className="font-mono text-amber-400">{stats.max_ppb?.toFixed(1)} ppb</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Estaciones activas</dt>
                  <dd className="font-mono text-slate-200">{stats.active_stations}</dd>
                </div>
              </dl>
            ) : (
              <Skeleton className="h-24 bg-slate-900/80" />
            )}
          </Card>
        </div>
      </div>

      {/* ── Arquitectura visual ── */}
      <Card className="mt-4 border-slate-800/80 bg-slate-900/60 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-400" />
          <h3 className="text-sm font-medium text-slate-200">Arquitectura del modelo</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {ARCH_LAYERS.map((layer, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className="rounded-lg border px-3 py-2 text-center"
                style={{
                  borderColor: `${layer.color}40`,
                  background: `${layer.color}10`,
                }}
              >
                <div className="text-xs font-semibold" style={{ color: layer.color }}>
                  {layer.name}
                </div>
                <div className="mt-0.5 text-[10px] text-slate-400">{layer.desc}</div>
              </div>
              {i < ARCH_LAYERS.length - 1 && (
                <div className="text-slate-600">→</div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          {[
            { label: "Funciones de pérdida", value: "12 (curriculum)" },
            { label: "Parámetros", value: "~47M" },
            { label: "Framework", value: "PyTorch 2.x" },
            { label: "Exportación", value: "ONNX Runtime" },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-lg border border-slate-800 bg-slate-950/40 p-2.5 text-center"
            >
              <div className="font-mono text-sm text-slate-200">{item.value}</div>
              <div className="mt-0.5 text-slate-500">{item.label}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
