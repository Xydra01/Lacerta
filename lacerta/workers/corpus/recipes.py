"""Corpus recipes."""

from __future__ import annotations

from lacerta.core.capabilities import Recipe, register_recipe

CORPUS_RECIPES = {
    "corpus.index_sources": Recipe(
        recipe_id="corpus.index_sources",
        title="Index corpus sources",
        description="extract → chunk → map → keyword index → complete",
        capability_ids=(
            "corpus.extract",
            "corpus.chunk",
            "corpus.map",
            "corpus.embed",
        ),
    ),
}


def register_corpus_recipes() -> None:
    for recipe in CORPUS_RECIPES.values():
        register_recipe(recipe)


register_corpus_recipes()
