"""Research recipes."""

from __future__ import annotations

from lacerta.core.capabilities import Recipe, register_recipe

RESEARCH_RECIPES = {
    "research.offline": Recipe(
        recipe_id="research.offline",
        title="Offline research",
        description="Ingest → synthesize → finalize",
        capability_ids=(
            "research.ingest_offline",
            "research.synthesize_notes",
            "research.finalize_deliverable",
        ),
    ),
    "research.full_web": Recipe(
        recipe_id="research.full_web",
        title="Full web research",
        description="Gather → synthesize → finalize",
        capability_ids=(
            "research.gather_web_sources",
            "research.synthesize_notes",
            "research.finalize_deliverable",
        ),
    ),
    "research.light": Recipe(
        recipe_id="research.light",
        title="Light web for chat",
        description="Light context",
        capability_ids=("research.light_web_context",),
    ),
}


def register_research_recipes() -> None:
    for r in RESEARCH_RECIPES.values():
        register_recipe(r)


register_research_recipes()
