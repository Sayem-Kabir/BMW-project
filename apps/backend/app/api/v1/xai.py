from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.common import XAIExplainRequest, XAIExplainResponse

router = APIRouter(prefix="/api/v1/xai", tags=["Explainable AI"])


@router.post("/explain", response_model=XAIExplainResponse)
async def explain(body: XAIExplainRequest):
    return XAIExplainResponse(
        explanation=(
            "XAI scaffold: Grad-CAM and SHAP explanations will be generated "
            "once CV/ML models are trained (Phase 6)."
        ),
        method="scaffold",
        heatmap_url=None,
        shap_values=None,
    )


@router.get("/heatmap/{filename}")
async def get_heatmap(filename: str):
    return JSONResponse(
        {
            "filename": filename,
            "status": "not_available",
            "message": "Heatmap storage ships with Phase 6 XAI",
            "phase": "scaffold",
        }
    )
