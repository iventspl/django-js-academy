"""Starter contract for the AI Product Capstone project.

Replace the stub response with your grounded answer pipeline. Keep the API
contract: a health check and a typed /ask endpoint with validated input.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[str]


app = FastAPI(title="AI Product Capstone")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if not request.question.strip():
        # Pydantic/FastAPI should return 422 for an empty question too; keep a
        # second guard here so the contract is explicit.
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="question is required")
    return AskResponse(answer="Not implemented yet.", citations=[])
