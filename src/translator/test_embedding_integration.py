# запуск: flirtello-backend-service $ python -m dotenv -f src/.env run -- pytest -rs src/translator/test_embedding_integration.py

import os

import pytest

from .in_memory import InMemoryTranslationMemory
from .prod_embedding import MixedbreadEmbeddingService
from .utils import cosine_similarity

pytestmark = []  # Не скипаем модулем, дадим детальную причину внутри теста


def _has_api_key() -> bool:
    return bool(os.getenv("EMBEDDINGS_API_KEY") or os.getenv("TRANSLATOR_EMBEDDINGS_API_KEY"))


#@pytest.mark.integration
def test_mixedbread_embeddings_cat_vs_apple():
    reasons: list[str] = []
    if os.getenv("TRANSLATOR_EMBEDDING_IMPL", "").lower() != "mixedbread":
        reasons.append("TRANSLATOR_EMBEDDING_IMPL != mixedbread")
    if not _has_api_key():
        reasons.append("Missing EMBEDDINGS_API_KEY or TRANSLATOR_EMBEDDINGS_API_KEY")
    if reasons:
        pytest.skip("Integration prerequisites not met: " + "; ".join(reasons))

    try:
        svc = MixedbreadEmbeddingService()
    except (ImportError, ValueError) as exc:
        pytest.skip(f"MixedbreadEmbeddingService unavailable: {exc}")

    cat1 = (
        "Домашняя кошка мирно спит на мягком диване и тихо мурлычет. "
        "Её шерсть тёплая, а лапы аккуратно поджаты."
    )
    cat2 = (
        "Кот играет с клубком шерсти на ковре в гостиной и тоже мурлычет. "
        "Иногда он переворачивается на спину и вытягивает лапы."
    )
    finance = (
        "Фондовые индексы снизились после заявления центрального банка о повышении ключевой ставки. "
        "Инвесторы пересматривают оценки рисков, а волатильность растёт на фоне новых макроэкономических данных."
    )
    tech = (
        "Новая версия операционной системы получила улучшенный планировщик задач и поддержку ускоренного ИИ‑инференса. "
        "Производительность возросла, а энергопотребление снизилось благодаря оптимизациям ядра."
    )
    medical = (
        "Клинические испытания продемонстрировали статистически значимое снижение симптомов у пациентов. "
        "Исследование проведено в двойном слепом рандомизированном формате."
    )
    sports = (
        "Команда одержала победу в дополнительное время после серии острых атак. "
        "Тренер отметил высокую дисциплину и готовность игроков."
    )

    v1 = svc.embed(cat1)
    v2 = svc.embed(cat2)
    v_fin = svc.embed(finance)
    v_tech = svc.embed(tech)
    v_med = svc.embed(medical)
    v_sports = svc.embed(sports)

    assert v1 and v2 and v_fin and v_tech and v_med and v_sports, "Embeddings must be non-empty"

    sim_cats = cosine_similarity(v1, v2)
    negatives = [
        ("finance", cosine_similarity(v1, v_fin)),
        ("tech", cosine_similarity(v1, v_tech)),
        ("medical", cosine_similarity(v1, v_med)),
        ("sports", cosine_similarity(v1, v_sports)),
    ]
    worst_neg_name, worst_neg_sim = max(negatives, key=lambda x: x[1])

    # Проверяем ранжирование: кошка-кошка должна быть ближе, чем любой из негативов
    assert sim_cats > worst_neg_sim, (sim_cats, worst_neg_name, worst_neg_sim, negatives)


def _skip_if_mixedbread_unavailable():
    reasons: list[str] = []
    if os.getenv("TRANSLATOR_EMBEDDING_IMPL", "").lower() != "mixedbread":
        reasons.append("TRANSLATOR_EMBEDDING_IMPL != mixedbread")
    if not _has_api_key():
        reasons.append("Missing EMBEDDINGS_API_KEY or TRANSLATOR_EMBEDDINGS_API_KEY")
    if reasons:
        pytest.skip("Integration prerequisites not met: " + "; ".join(reasons))


def test_tm_nearest_neighbor_medical_domain_wins():
    _skip_if_mixedbread_unavailable()

    try:
        svc = MixedbreadEmbeddingService()
    except (ImportError, ValueError) as exc:
        pytest.skip(f"MixedbreadEmbeddingService unavailable: {exc}")

    tm = InMemoryTranslationMemory()

    corpus = [
        # cats
        ("Кошка свернулась клубочком и тихо мурлычет на пледе.", "cats"),
        ("Кот играет с клубком шерсти и прыгает на диван.", "cats"),
        # finance
        (
            "Фондовый рынок открылся снижением после публикации отчёта по инфляции.",
            "finance",
        ),
        (
            "Центральный банк сохранил ключевую ставку без изменений на текущем заседании.",
            "finance",
        ),
        # tech
        (
            "Компания представила обновлённый чип с ускорением ИИ-инференса и меньшим потреблением энергии.",
            "tech",
        ),
        (
            "Новая версия ОС получила улучшенный планировщик и оптимизации ядра.",
            "tech",
        ),
        # medical
        (
            "Клинические испытания показали снижение симптомов у пациентов по сравнению с плацебо.",
            "medical",
        ),
        (
            "Исследование проведено в рандомизированном двойном слепом формате и продемонстрировало эффективность терапии.",
            "medical",
        ),
        # sports
        ("Команда выиграла матч в дополнительное время, сделав решающий гол.", "sports"),
        ("Тренер отметил отличную подготовку и дисциплину игроков.", "sports"),
    ]

    src_to_label = {}
    for text, label in corpus:
        vec = svc.embed(text)
        tm.add(text, target_text=label, embedding=vec)
        src_to_label[text] = label

    query = (
        "Пациенты, получавшие новую терапию, продемонстрировали статистически значимое улучшение показателей."
    )
    q_vec = svc.embed(query)
    matches = tm.search_by_embedding(q_vec, limit=5)

    assert matches, "TM should return at least one match"
    top = matches[0]
    top_label = src_to_label.get(top.source_text, top.target_text)

    # Проверяем, что ближайший пример из медицинского домена
    assert top_label == "medical", (top_label, [(m.source_text, m.score) for m in matches])


