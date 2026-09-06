"""Learn recipes."""

from __future__ import annotations

from lacerta.core.capabilities import Recipe, register_recipe

LEARN_RECIPES = {
    "learn.syllabus_from_files": Recipe(
        recipe_id="learn.syllabus_from_files",
        title="Syllabus from files",
        description="Ingest attachments → write syllabus → finalize",
        capability_ids=(
            "learn.ingest_course_materials",
            "learn.write_syllabus",
            "learn.finalize_course",
        ),
    ),
    "learn.syllabus_from_web": Recipe(
        recipe_id="learn.syllabus_from_web",
        title="Syllabus from topic + web",
        description="Gather → ingest → write → finalize (gather stubbed in L3)",
        capability_ids=(
            "learn.gather_topic_sources",
            "learn.ingest_course_materials",
            "learn.write_syllabus",
            "learn.finalize_course",
        ),
    ),
}


def register_learn_recipes() -> None:
    for recipe in LEARN_RECIPES.values():
        register_recipe(recipe)


register_learn_recipes()
