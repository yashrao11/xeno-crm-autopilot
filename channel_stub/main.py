import asyncio
import random
from typing import Optional

import httpx
from fastapi import FastAPI, status
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Channel Stub", description="Mock external messaging channel service")

POSITIVE_REPLIES = [
    "I love this product, ordering more!",
    "Great offer, please send me the checkout link.",
    "Thanks for reaching out — I'm interested!",
    "Perfect timing, I was just about to reorder.",
    "Awesome discount, count me in!",
]

NEGATIVE_REPLIES = [
    "Too expensive, switching brands.",
    "Please stop messaging me.",
    "Not interested, cancel my subscription.",
    "Bad experience last time, never again.",
    "No thanks, I already bought elsewhere.",
]

NEUTRAL_REPLIES = [
    "Can you share more details?",
    "Maybe later, remind me next week.",
    "What are the shipping charges?",
    "Is this offer valid on all products?",
    "I'll think about it and get back to you.",
]

# Probability of advancing to each subsequent stage after the initial delay.
STAGE_PIPELINE: list[tuple[str, float]] = [
    ("sent", 1.0),
    ("delivered", 1.0),
    ("read", 0.85),
    ("clicked", 0.35),
    ("replied", 0.30),
]


class SimulateRequest(BaseModel):
    communication_log_id: int
    webhook_url: HttpUrl
    campaign_id: Optional[int] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    channel: Optional[str] = None
    message: Optional[str] = None


class SimulateAcceptedResponse(BaseModel):
    communication_log_id: int
    status: str = "accepted"


def _generate_customer_reply() -> str:
    roll = random.random()
    if roll < 0.45:
        return random.choice(POSITIVE_REPLIES)
    if roll < 0.75:
        return random.choice(NEGATIVE_REPLIES)
    return random.choice(NEUTRAL_REPLIES)


async def _run_delivery_simulation(payload: SimulateRequest) -> None:
    await asyncio.sleep(random.uniform(1, 5))

    webhook_url = str(payload.webhook_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for stage_status, advance_probability in STAGE_PIPELINE:
            if random.random() > advance_probability:
                break

            body: dict[str, object] = {
                "communication_log_id": payload.communication_log_id,
                "status": stage_status,
            }
            if stage_status == "replied":
                body["customer_reply"] = _generate_customer_reply()

            try:
                await client.post(webhook_url, json=body)
            except httpx.HTTPError:
                return

            if stage_status != STAGE_PIPELINE[-1][0]:
                await asyncio.sleep(random.uniform(0.3, 1.0))


@app.post(
    "/simulate",
    response_model=SimulateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def simulate(payload: SimulateRequest) -> SimulateAcceptedResponse:
    asyncio.create_task(_run_delivery_simulation(payload))
    return SimulateAcceptedResponse(communication_log_id=payload.communication_log_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
