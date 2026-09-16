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
    "learn.tutor_turn": Recipe(
        recipe_id="learn.tutor_turn",
        title="Tutor turn",
        description="One grounded tutor reply from syllabus + bounded notes or corpus retrieve",
        capability_ids=("learn.tutor_turn",),
    ),
    "learn.assessment": Recipe(
        recipe_id="learn.assessment",
        title="Generate assessments",
        description="Write structured assessments under assessments/",
        capability_ids=("learn.generate_assessments",),
    ),
    "learn.mastery_check": Recipe(
        recipe_id="learn.mastery_check",
        title="Mastery check",
        description="Generate MC mastery check for one syllabus node",
        capability_ids=("learn.mastery_check",),
    ),
    "learn.practice_quiz": Recipe(
        recipe_id="learn.practice_quiz",
        title="Practice quiz",
        description="Generate MC practice quiz (± corpus retrieve)",
        capability_ids=("learn.generate_quiz",),
    ),
    "learn.archive_chat": Recipe(
        recipe_id="learn.archive_chat",
        title="Archive chat",
        description="Retrieve-grounded archive reply",
        capability_ids=("learn.archive_chat",),
    ),
    "learn.index_corpus": Recipe(
        recipe_id="learn.index_corpus",
        title="Index course corpus",
        description="Multi-pass index via shared corpus.index_sources",
        capability_ids=(
            "corpus.extract",
            "corpus.chunk",
            "corpus.map",
            "corpus.embed",
        ),
    ),
}


def register_learn_recipes() -> None:
    for recipe in LEARN_RECIPES.values():
        register_recipe(recipe)


register_learn_recipes()
