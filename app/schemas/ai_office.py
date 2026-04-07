"""Pydantic schemas for the AI Office endpoints."""

from pydantic import BaseModel, Field


class TestWhatsAppBody(BaseModel):
    phone: str = Field(..., description="Phone in E.164 format (e.g. +5491158399708)")
    message: str = Field(
        default=(
            "Hola! Esto es una prueba de Mote, el agente de Scouter. "
            "Si recibiste esto, el outreach funciona correctamente."
        ),
        max_length=500,
    )


class CloserReplyBody(BaseModel):
    client_message: str = Field(..., description="Client's inbound message")
