"""Turkish notification texts.

Only identifying metadata is included (document, section, revision number,
dates). The revision content column is never sent - it may contain
confidential change details that do not belong in a notification channel.
"""

from __future__ import annotations

from .models import PlannedNotification

DATE_FMT = "%d.%m.%Y"


def title_for(p: PlannedNotification) -> str:
    if p.is_overdue:
        return "🔴 QMM Talimatı – GEÇERLİLİK SÜRESİ DOLDU"
    return "⚠️ QMM Talimatı – Güncelleme Hatırlatması"


def summary_for(p: PlannedNotification) -> str:
    due = p.document.due_date.strftime(DATE_FMT)
    if p.is_overdue:
        days = -p.days_left
        return (
            f"Bu talimatın geçerlilik süresi {due} tarihinde doldu "
            f"({days} gün geçti) ve henüz güncellenmedi. "
            "Lütfen revizyonu en kısa sürede tamamlayınız."
        )
    if p.days_left == 0:
        return (
            f"Bu talimatın geçerlilik süresi BUGÜN ({due}) doluyor. "
            "Lütfen revizyonu tamamlayınız."
        )
    if p.days_left == 1:
        return (
            f"Bu talimatın geçerlilik süresi YARIN ({due}) doluyor. "
            "Lütfen revizyonu tamamlayınız."
        )
    return (
        f"Bu talimatın geçerlilik süresinin dolmasına {p.days_left} gün kaldı "
        f"(son geçerlilik tarihi: {due}). Lütfen revizyonu planlayınız."
    )


def facts_for(p: PlannedNotification) -> list[tuple[str, str]]:
    d = p.document
    facts = [
        ("Doküman", d.title),
        ("Bölüm", d.section or "-"),
        ("Revizyon No", d.revision_no or "-"),
        ("Hazırlayan", d.prepared_by or "-"),
        ("Son Geçerlilik Tarihi", d.due_date.strftime(DATE_FMT)),
    ]
    if d.revision_date:
        facts.insert(3, ("Son Revizyon Tarihi", d.revision_date.strftime(DATE_FMT)))
    return facts


def plain_text_for(p: PlannedNotification) -> str:
    lines = [title_for(p), ""]
    lines += [f"{k}: {v}" for k, v in facts_for(p)]
    lines += ["", summary_for(p)]
    lines += ["", "Bu bildirim QMM hatırlatma otomasyonu tarafından gönderilmiştir."]
    return "\n".join(lines)
