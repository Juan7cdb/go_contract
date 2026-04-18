import asyncio
import sys
import os

# Add the app directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.core.database import async_session_maker, engine
from app.models import Plan, TemplateContract, Agent
from sqlalchemy.ext.asyncio import AsyncSession

async def seed_data():
    print("Starting database seeding...")
    async with async_session_maker() as db:
        # 1. Seed Plans
        plans_data = [
            {
                "id": 1,
                "title": "Free",
                "description": "Prueba básica para redactar tus primeros contratos.",
                "price": 0.0,
                "contracts_included": 2,
                "time_subscription": "lifetime"
            },
            {
                "id": 2,
                "title": "Pro",
                "description": "Ideal para profesionales e independientes.",
                "price": 29.99,
                "contracts_included": 15,
                "time_subscription": "monthly"
            },
            {
                "id": 3,
                "title": "Enterprise",
                "description": "Contratos ilimitados para grandes empresas.",
                "price": 99.99,
                "contracts_included": 1000,
                "time_subscription": "monthly"
            }
        ]

        for p_data in plans_data:
            result = await db.execute(select(Plan).where(Plan.id == p_data["id"]))
            if not result.scalar_one_or_none():
                plan = Plan(**p_data)
                db.add(plan)
                print(f"Added plan: {p_data['title']}")

        # 2. Seed Template Contracts
        templates_data = [
            {
                "id": 1,
                "category": "immigration",
                "title": "Immigration Legal Services Agreement",
                "description": "Acuerdo de servicios legales para trámites migratorios (Visa, Residencia, etc.)",
                "rules": """- DEBE incluir una cláusula de NO GARANTÍA de resultados (USCIS).
- DEBE especificar honorarios fijos (Flat Fee).
- DEBE aclarar que los gastos de gobierno no están incluidos.
- Jurisdicción principal: Leyes Federales de EE.UU. e Inmigración."""
            },
            {
                "id": 2,
                "category": "corporate",
                "subcategory": "hr",
                "title": "Termination Agreement",
                "description": "Acuerdo mutuo de terminación de contrato laboral o de servicios.",
                "rules": """- DEBE incluir liberación mutua de responsabilidad (Mutual Release).
- DEBE especificar el último pago y liquidación de beneficios.
- DEBE incluir confidencialidad post-terminación.
- DEBE incluir cláusula de no-difamación."""
            },
            {
                "id": 3,
                "category": "construction",
                "title": "Subcontractor Agreement",
                "description": "Contrato para subcontratistas en proyectos de construcción o servicios especializados.",
                "rules": """- DEBE incluir cláusula 'Pay-when-paid' (Pague cuando le paguen).
- DEBE exigir seguros de responsabilidad civil mínimos.
- DEBE incluir cumplimiento de normas de seguridad (OSHA).
- Cláusulas de retención de garantía (Warranty period)."""
            },
            {
                "id": 4,
                "category": "brand",
                "title": "Influencer Agreement",
                "description": "Contrato para campañas de marketing con influencers y creadores de contenido.",
                "rules": """- DEBE cumplir con las guías de la FTC (Divulgación de publicidad).
- DEBE especificar la propiedad intelectual de los contenidos (Influencer vs Marca).
- DEBE detallar el número exacto de posts/stories.
- Cláusula de moralidad y aprobación previa de marca."""
            }
        ]

        for t_data in templates_data:
            result = await db.execute(select(TemplateContract).where(TemplateContract.id == t_data["id"]))
            if not result.scalar_one_or_none():
                template = TemplateContract(**t_data)
                db.add(template)
                print(f"Added template: {t_data['title']}")

        # 3. Seed Default Agents for these templates
        agents_data = [
            {
                "template_id": 1,
                "title": "Asistente Legal de Inmigración",
                "prompt": "Eres un asistente legal experto en inmigración. Ayuda al usuario a llenar los datos para su acuerdo de servicios migratorios. Asegúrate de que entienda que no hay garantías de aprobación."
            },
            {
                "template_id": 2,
                "title": "Mediador de Terminación",
                "prompt": "Eres un experto en relaciones laborales. Ayuda a redactar una terminación justa y mutuamente beneficiosa, protegiendo a ambas partes de litigios futuros."
            },
            {
                "template_id": 3,
                "title": "Coordinador de Subcontratistas",
                "prompt": "Eres un gestor de proyectos de construcción. Enfócate en el cumplimiento técnico, seguros y plazos de entrega."
            },
            {
                "template_id": 4,
                "title": "Manager de Campañas",
                "prompt": "Eres un experto en marketing digital. Ayuda a definir hitos claros de contenido y cumplimiento de normativas de publicidad."
            }
        ]

        for a_data in agents_data:
            result = await db.execute(select(Agent).where(Agent.template_id == a_data["template_id"]))
            if not result.scalar_one_or_none():
                agent = Agent(**a_data)
                db.add(agent)
                print(f"Added agent for template ID: {a_data['template_id']}")

        await db.commit()
        print("Success: Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_data())
