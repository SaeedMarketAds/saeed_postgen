from __future__ import annotations

import base64
import binascii
import io
import os
import secrets
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from core.engines import generate_ad_card

app = FastAPI(
    title="Saeed PostGen API",
    description="API interface for the original Saeed PostGen engine",
    version="1.0.0",
)


class AdCardRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    price: str = Field(default="", max_length=100)
    specifications: str = Field(default="", max_length=1000)
    contact: str = Field(default="", max_length=200)
    brand: str = Field(default="Saeed PostGen", max_length=100)
    template: str = Field(default="gold", max_length=30)
    product_image_base64: str | None = None


@app.get("/v1/health")
def health_check():
    return {
        "status": "online",
        "system": "Saeed PostGen",
        "api_version": "v1",
    }


def verify_api_key(api_key: str | None):
    expected = os.getenv("POSTGEN_API_KEY", "")

    if not expected:
        raise HTTPException(status_code=503, detail="API key is not configured.")

    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key.")


@app.post("/v1/ad-card")
def create_ad_card(
    request: AdCardRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    verify_api_key(x_api_key)

    product_image = None

    if request.product_image_base64:
        encoded_image = request.product_image_base64

        if "," in encoded_image:
            encoded_image = encoded_image.split(",", 1)[1]

        if len(encoded_image) > 12_000_000:
            raise HTTPException(status_code=413, detail="Product image is too large.")

        try:
            image_bytes = base64.b64decode(encoded_image, validate=True)

            if len(image_bytes) > 8_000_000:
                raise HTTPException(status_code=413, detail="Decoded image is too large.")

            product_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        except HTTPException:
            raise
        except (ValueError, binascii.Error, UnidentifiedImageError):
            raise HTTPException(status_code=400, detail="Invalid product image.")

    filename = f"api_{uuid.uuid4().hex}.png"
    output_path = None

    try:
        result = generate_ad_card(
            product_name=request.product_name,
            price=request.price,
            specifications=request.specifications,
            contact=request.contact,
            brand=request.brand,
            template=request.template,
            product_image=product_image,
            filename=filename,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=422,
                detail={
                    "status": result.get("status"),
                    "message": result.get("message"),
                },
            )

        image = result.get("image")
        if image is None:
            raise HTTPException(
                status_code=500,
                detail="The PostGen engine returned no image.",
            )

        output_path = Path(result["path"])

        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")

        return Response(
            content=image_buffer.getvalue(),
            media_type="image/png",
            headers={
                "X-PostGen-Status": str(result.get("status", "SUCCESS")),
            },
        )

    finally:
        if output_path is not None:
            output_path.unlink(missing_ok=True)
