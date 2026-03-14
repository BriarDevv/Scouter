"""Seed script: insert example leads for testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.lead_source import LeadSource, SourceType
from app.schemas.lead import LeadCreate
from app.services.lead_service import create_lead
from app.models.territory import Territory

SAMPLE_LEADS = [
    {
        "business_name": "Cafe El Molino",
        "industry": "restaurante",
        "city": "Buenos Aires",
        "zone": "Palermo",
        "instagram_url": "https://instagram.com/cafeelmolino",
        "phone": "+5411-4567-8901",
    },
    {
        "business_name": "Peluqueria Estilo",
        "industry": "peluqueria",
        "city": "Rosario",
        "email": "info@peluqueriaestilo.com",
        "website_url": "https://peluqueriaestilo.wixsite.com/home",
    },
    {
        "business_name": "Taller Mecanico Rodriguez",
        "industry": "taller",
        "city": "Cordoba",
        "phone": "+54351-123-4567",
    },
    {
        "business_name": "Boutique Luna",
        "industry": "indumentaria",
        "city": "Buenos Aires",
        "zone": "Recoleta",
        "instagram_url": "https://instagram.com/boutiqueluna",
        "website_url": "https://boutiqueluna.com",
        "email": "ventas@boutiqueluna.com",
    },
    {
        "business_name": "Consultorio Dra. Perez",
        "industry": "clinica",
        "city": "Mendoza",
        "phone": "+54261-555-1234",
    },
]


def main():
    db = SessionLocal()
    try:
        # Create a manual source
        source = LeadSource(name="seed_data", source_type=SourceType.MANUAL, description="Initial seed data")
        db.add(source)
        db.commit()
        db.refresh(source)

        for lead_data in SAMPLE_LEADS:
            lead_data["source_id"] = source.id
            lead = create_lead(db, LeadCreate(**lead_data))
            print(f"Created: {lead.business_name} ({lead.id})")

        # Create sample territories
        territories_data = [
            {
                "name": "CABA",
                "description": "Ciudad Autonoma de Buenos Aires",
                "color": "#8b5cf6",
                "cities": ["Buenos Aires", "Palermo", "Recoleta", "Belgrano", "Caballito",
                           "Villa Urquiza", "Flores", "Barracas", "Almagro", "Villa Crespo", "Boedo"],
            },
            {
                "name": "GBA Norte",
                "description": "Gran Buenos Aires zona norte",
                "color": "#3b82f6",
                "cities": ["San Isidro", "Tigre", "Vicente Lopez", "San Martin"],
            },
            {
                "name": "Interior Cordoba",
                "description": "Provincia de Cordoba",
                "color": "#22c55e",
                "cities": ["Cordoba", "Rio Cuarto"],
            },
        ]
        for tdata in territories_data:
            t = Territory(**tdata)
            db.add(t)
        db.commit()
        print(f"Seeded {len(territories_data)} territories.")

        print(f"\nSeeded {len(SAMPLE_LEADS)} leads.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
