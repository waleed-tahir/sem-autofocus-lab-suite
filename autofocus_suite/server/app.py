"""
FastAPI Server for Electron Microscope Autofocus Lab Suite
Provides high-performance REST endpoints for:
- Precomputed 10-FMO curves & astigmatism diagnostics
- Ablation tournament results & leaderboard
- Live real-time search execution with step-by-step trajectory
- Micrograph frame streaming with dynamic ROI bounding boxes
"""

from __future__ import annotations
import os
import sys
import json
import io
from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from autofocus_suite.core.autofocus_engine import AutofocusEngine
from autofocus_suite.core.fmo_kernels import FMO_METADATA, FMO_REGISTRY
from autofocus_suite.core.search_algorithms import SEARCH_METADATA, SEARCH_REGISTRY
from autofocus_suite.core.preconditioning import anscombe_stabilize

DATA_DIR = os.path.join(BASE_DIR, "datasets")
RESULTS_DIR = os.path.join(BASE_DIR, "autofocus_suite", "benchmark", "results")

CURVES_CACHE_FILE = os.path.join(RESULTS_DIR, "curves_cache.json")
BENCHMARK_RESULTS_FILE = os.path.join(RESULTS_DIR, "ablation_results.json")
ASTIGMATISM_CACHE_FILE = os.path.join(RESULTS_DIR, "astigmatism_cache.json")

app = FastAPI(
    title="Electron Microscope Autofocus Lab Suite API",
    description="Backend service for SEM/TEM Autofocus 10-Method Analysis",
    version="2.0.0"
)

# Enable CORS for local Vite dev server and desktop webviews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunSearchRequest(BaseModel):
    dataset: str
    fmo: str = "m1_scharr"
    search_method: str = "s2_hybrid"
    top_k_rois: int = 3
    use_anscombe: bool = False


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    datasets = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    has_curves = os.path.exists(CURVES_CACHE_FILE)
    has_benchmark = os.path.exists(BENCHMARK_RESULTS_FILE)
    has_astig = os.path.exists(ASTIGMATISM_CACHE_FILE)

    return {
        "status": "online",
        "version": "2.0.0",
        "available_datasets": datasets,
        "caches_ready": {
            "curves": has_curves,
            "benchmark": has_benchmark,
            "astigmatism": has_astig
        }
    }


CURRENT_DATA_DIR = os.path.join(BASE_DIR, "datasets")


class SetDatasetPathRequest(BaseModel):
    path: str


@app.get("/api/dataset-path")
def get_dataset_path() -> Dict[str, Any]:
    return {
        "path": CURRENT_DATA_DIR,
        "default_path": os.path.join(BASE_DIR, "datasets"),
        "exists": os.path.isdir(CURRENT_DATA_DIR)
    }


@app.post("/api/dataset-path")
def set_dataset_path(req: SetDatasetPathRequest) -> Dict[str, Any]:
    global CURRENT_DATA_DIR
    clean_path = os.path.abspath(req.path.strip().strip('"').strip("'"))
    if not os.path.isdir(clean_path):
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {clean_path}")
    CURRENT_DATA_DIR = clean_path
    datasets = get_datasets()
    return {
        "status": "ok",
        "path": CURRENT_DATA_DIR,
        "datasets": datasets,
        "count": len(datasets)
    }


@app.get("/api/datasets")
def get_datasets() -> List[Dict[str, Any]]:
    results = []
    if not os.path.isdir(CURRENT_DATA_DIR):
        return results

    # Check for subdirectories containing image focal stacks
    subdirs = [d for d in sorted(os.listdir(CURRENT_DATA_DIR)) if os.path.isdir(os.path.join(CURRENT_DATA_DIR, d))]
    
    # Also check if CURRENT_DATA_DIR itself contains images directly
    direct_images = [
        f for f in sorted(os.listdir(CURRENT_DATA_DIR)) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))
    ]

    target_folders = []
    if subdirs:
        for d in subdirs:
            target_folders.append((d, os.path.join(CURRENT_DATA_DIR, d)))
    elif direct_images:
        target_folders.append((os.path.basename(CURRENT_DATA_DIR), CURRENT_DATA_DIR))

    for name, ds_path in target_folders:
        images = [
            f for f in sorted(os.listdir(ds_path)) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))
        ]
        if not images:
            continue
            
        h, w = 768, 1024
        first = cv2.imread(os.path.join(ds_path, images[0]), cv2.IMREAD_GRAYSCALE)
        if first is not None:
            h, w = first.shape[:2]
        
        regime = "Standard SEM"
        if "spd1" in name:
            regime = "Clean / High SNR SEM"
        elif "spd2" in name:
            regime = "Standard SNR SEM"
        elif "spd3" in name:
            regime = "Moderate Noise SEM"
        elif "spd5" in name:
            regime = "Heavy Shot Noise SEM"

        results.append({
            "id": name,
            "name": name,
            "path": ds_path,
            "regime": regime,
            "num_frames": len(images),
            "resolution": f"{w}x{h}",
            "width": w,
            "height": h
        })
    return results


@app.get("/api/metadata")
def get_metadata() -> Dict[str, Any]:
    return {
        "fmos": FMO_METADATA,
        "search_algorithms": SEARCH_METADATA
    }


@app.get("/api/curves/{dataset_name}")
def get_curves(dataset_name: str) -> Dict[str, Any]:
    if not os.path.exists(CURVES_CACHE_FILE):
        raise HTTPException(status_code=503, detail="Curves cache not ready yet")
    with open(CURVES_CACHE_FILE, "r") as f:
        data = json.load(f)
    if dataset_name not in data:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_name} not found in cache")
    return data[dataset_name]


@app.get("/api/astigmatism/{dataset_name}")
def get_astigmatism(dataset_name: str) -> Dict[str, Any]:
    if not os.path.exists(ASTIGMATISM_CACHE_FILE):
        raise HTTPException(status_code=503, detail="Astigmatism cache not ready yet")
    with open(ASTIGMATISM_CACHE_FILE, "r") as f:
        data = json.load(f)
    if dataset_name not in data:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_name} not found in cache")
    return data[dataset_name]


@app.get("/api/benchmark-matrix")
def get_benchmark_matrix() -> Dict[str, Any]:
    if not os.path.exists(BENCHMARK_RESULTS_FILE):
        raise HTTPException(status_code=503, detail="Benchmark results not ready yet")
    with open(BENCHMARK_RESULTS_FILE, "r") as f:
        return json.load(f)


@app.post("/api/run-search")
def run_live_search(req: RunSearchRequest) -> Dict[str, Any]:
    ds_path = os.path.join(CURRENT_DATA_DIR, req.dataset)
    if not os.path.isdir(ds_path):
        ds_path = CURRENT_DATA_DIR
    if not os.path.isdir(ds_path):
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset} not found")

    # Load ground truth if available
    z_gt = None
    ref_curve = None
    if os.path.exists(CURVES_CACHE_FILE):
        try:
            with open(CURVES_CACHE_FILE, "r") as f:
                cdata = json.load(f)
            if req.dataset in cdata:
                z_gt = cdata[req.dataset]["ground_truth_peaks"].get(req.fmo)
                ref_curve = cdata[req.dataset]["curves"].get(req.fmo)
        except Exception:
            pass

    engine = AutofocusEngine(
        dataset_path=ds_path,
        fmo=req.fmo,
        search_method=req.search_method,
        top_k_rois=req.top_k_rois,
        use_anscombe=req.use_anscombe
    )

    result = engine.run_autofocus(ground_truth_peak=z_gt, reference_curve=ref_curve)
    result["dataset"] = req.dataset
    result["ground_truth_peak"] = z_gt
    return result


@app.get("/api/frame/{dataset_name}/{frame_idx}")
def get_frame(
    dataset_name: str,
    frame_idx: int,
    overlay_rois: bool = Query(False),
    top_k: int = Query(3),
    anscombe: bool = Query(False)
):
    ds_path = os.path.join(CURRENT_DATA_DIR, dataset_name)
    if not os.path.isdir(ds_path):
        ds_path = CURRENT_DATA_DIR
    if not os.path.isdir(ds_path):
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_name} not found")

    images = sorted(os.listdir(ds_path))
    if frame_idx < 0 or frame_idx >= len(images):
        raise HTTPException(status_code=400, detail="Frame index out of bounds")

    img_path = os.path.join(ds_path, images[frame_idx])
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to read image")

    if anscombe:
        img_stab = anscombe_stabilize(img)
        # Normalize to 0-255 for display
        img_stab = cv2.normalize(img_stab, None, 0, 255, cv2.NORM_MINMAX)
        img = img_stab.astype(np.uint8)

    # Convert to BGR for drawing colored ROI bounding boxes
    bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if overlay_rois:
        # Dynamic 9-zone ROI calculation
        h, w = img.shape[:2]
        bh, bw = h // 5, w // 5
        candidates = []
        for r in range(1, 4):
            for c in range(1, 4):
                y0, y1 = r * bh, (r + 1) * bh
                x0, x1 = c * bw, (c + 1) * bw
                patch = img[y0:y1:2, x0:x1:2]
                candidates.append((float(np.var(patch)), (y0, y1, x0, x1)))
        candidates.sort(key=lambda item: item[0], reverse=True)

        # Draw non-selected zones in translucent subtle blue
        for rank, (_, (y0, y1, x0, x1)) in enumerate(candidates):
            if rank >= top_k:
                cv2.rectangle(bgr, (x0, y0), (x1, y1), (180, 100, 50), 1)

        # Draw selected Top-K zones in bright Apple emerald/cyan
        colors = [(60, 230, 80), (0, 215, 255), (240, 150, 40)]
        for rank, (_, (y0, y1, x0, x1)) in enumerate(candidates[:top_k]):
            col = colors[rank % len(colors)]
            cv2.rectangle(bgr, (x0, y0), (x1, y1), col, 2)
            label = f"ROI #{rank+1}"
            cv2.putText(bgr, label, (x0 + 6, y0 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)

    success, encoded_img = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode image")

    return Response(content=encoded_img.tobytes(), media_type="image/jpeg")


# Mount static production UI build if available
UI_DIST_DIR = os.path.join(BASE_DIR, "autofocus_suite", "ui", "dist")
if os.path.exists(UI_DIST_DIR):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=UI_DIST_DIR, html=True), name="static_ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
