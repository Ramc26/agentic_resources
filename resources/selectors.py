def tokenize(text: str) -> set[str]:
    return {t for t in ''.join(c if c.isalnum() else ' ' for c in text.lower()).split() if t}


def rank_files_by_query(filenames: list[str], query: str) -> list[str]:
    """Simple relevance ranking by token overlap with special-casing common intents."""
    q = query.lower()
    q_tokens = tokenize(q)
    if not filenames:
        return []
    if 'log' in q:
        candidates = [f for f in filenames if 'log' in f.lower()]
        if candidates:
            return sorted(candidates)
    if 'note' in q or 'meeting' in q or 'discussion' in q:
        for name in ('project_notes.txt', 'notes.txt'):
            for f in filenames:
                if f.lower() == name:
                    return [f]
    def score(name: str) -> int:
        tokens = tokenize(name)
        return len(tokens & q_tokens)
    return [name for name in sorted(filenames, key=lambda n: (-score(n), n)) if score(name) > 0][:3]


