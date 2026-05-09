"""Inference jobs (MOCK hasta que se exporte el ONNX)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

JobStatus = Literal["queued", "running", "done", "failed"]


class InferenceMetrics(BaseModel):
    psnr: Optional[float] = None
    ssim: Optional[float] = None


class InferenceJob(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: str
    status: JobStatus = "queued"
    input_filename: str
    output_detection_ids: List[str] = []
    metrics: InferenceMetrics = InferenceMetrics()
    error: Optional[str] = None
    created_by: str
    runner: str = "demo-synthetic"


class InferenceJobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    runner: str = "demo-synthetic"
    warning: str


class ModelInfo(BaseModel):
    name: str
    weights_file: str
    weights_loaded: bool
    onnx_loaded: bool
    onnx_path: Optional[str]
    psnr_reported: float
    params: int
    trained_at: str
    notes: str
