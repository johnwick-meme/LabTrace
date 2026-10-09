
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.calculations import calculate_resistance, compare_readings
from core.memory import save_experiment, load_experiment, search_manual


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="LabTrace API", version="0.1.0")

app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


class ReadingRequest(BaseModel):
    reading_id: str
    voltage_v: float
    current_a: float


class CompareRequest(BaseModel):
    readings: list[ReadingRequest]
    tolerance: float = 0.05


class ExperimentRequest(BaseModel):
    experiment_id: str
    title: str = "Untitled experiment"
    raw_readings: list[ReadingRequest]
    observations: list[str] = []
    source_passages: list[dict] = []
    analysis_references: list[dict] = []


class ManualSearchRequest(BaseModel):
    query: str
    manual_text: str


@app.get("/")
def home():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "LabTrace API"}


@app.post("/api/calculate")
def calculate(request: ReadingRequest):
    try:
        return calculate_resistance(
            request.voltage_v,
            request.current_a,
        )
    except (ValueError, TypeError, OverflowError) as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/compare")
def compare(request: CompareRequest):
    try:
        return compare_readings(
            [reading.model_dump() for reading in request.readings],
            tolerance=request.tolerance,
        )
    except (ValueError, TypeError, OverflowError) as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/experiments")
def save(request: ExperimentRequest):
    try:
        return save_experiment(request.model_dump())
    except (ValueError, TypeError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.get("/api/experiments/{experiment_id}")
def load(experiment_id: str):
    try:
        experiment = load_experiment(experiment_id)
    except (ValueError, TypeError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error))

    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    return experiment


@app.post("/api/manual-search")
def manual_search(request: ManualSearchRequest):
    try:
        return {
            "passages": search_manual(request.query, request.manual_text)
        }
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error))


class InvestigateRequest(BaseModel):
    experiment_id: str
    name: str = "Ohm's Law Verification"
    readings: list[dict] = []
    manual_text: str | None = None
    reference_file: str = "ohms-law.md"


@app.post("/api/investigate")
def investigate(request: InvestigateRequest):
    """
    Run the full AI investigation with Gemma, Agent Skill, and deterministic tools.
    """
    from harness.agent import run_investigation

    payload = {
        "experiment_id": request.experiment_id,
        "name": request.name,
        "readings": request.readings,
    }
    if request.manual_text:
        payload["manual_text"] = request.manual_text
    if request.reference_file:
        payload["reference_file"] = request.reference_file

    result = run_investigation(payload)
    return result


class ChatRequest(BaseModel):
    message: str
    experiment_context: dict | None = None


@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    Interactive Chat assistant powered by local Gemma and Ohm's law reference.
    """
    from harness.agent import _load_reference, _call_ollama

    ref_text, _ = _load_reference("ohms-law.md")
    
    prompt_parts = [
        "You are LabTrace Assistant, an expert AI tutor for engineering students in a laboratory setting.",
        "Your role is to help students understand Ohm's law (V = IR), analyze inconsistent readings, and prepare for viva examinations.",
        "Be encouraging, concise, scientifically accurate, and never invent false experimental facts.",
        "",
        "=== REFERENCE MATERIAL ===",
        ref_text or "Ohm's law: V = IR.",
        "",
    ]

    if request.experiment_context:
        prompt_parts.append("=== CURRENT EXPERIMENT CONTEXT ===")
        prompt_parts.append(f"Experiment ID: {request.experiment_context.get('experiment_id', 'N/A')}")
        readings = request.experiment_context.get('readings') or request.experiment_context.get('raw_readings', [])
        for idx, r in enumerate(readings, 1):
            v = r.get('voltage', r.get('voltage_v'))
            c = r.get('current', r.get('current_a'))
            prompt_parts.append(f"Reading {idx}: {v} V, {c} A")
        prompt_parts.append("")

    prompt_parts.append(f"Student: {request.message}")
    prompt_parts.append("LabTrace Assistant:")

    full_prompt = "\n".join(prompt_parts)
    reply, error = _call_ollama(full_prompt)

    if error:
        raise HTTPException(status_code=503, detail=error)

    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
