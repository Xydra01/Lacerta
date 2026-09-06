"""Writing recipes."""

from __future__ import annotations

from lacerta.core.capabilities import Recipe, register_recipe

WRITING_RECIPES = {
    "writing.dynamic": Recipe(
        recipe_id="writing.dynamic",
        title="Draft then finalize",
        description="Default short path",
        capability_ids=(
            "writing.draft_sections",
            "writing.finalize_deliverable",
        ),
    ),
    "writing.from_sources": Recipe(
        recipe_id="writing.from_sources",
        title="From sources",
        description="Ingest → draft → finalize",
        capability_ids=(
            "writing.ingest_sources",
            "writing.draft_sections",
            "writing.finalize_deliverable",
        ),
    ),
}


def register_writing_recipes() -> None:
    for r in WRITING_RECIPES.values():
        register_recipe(r)


register_writing_recipes()
