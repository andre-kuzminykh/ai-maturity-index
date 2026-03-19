def __getattr__(name):
    if name in ("async_session", "engine", "Base"):
        from app.db.engine import async_session, engine, Base
        mapping = {"async_session": async_session, "engine": engine, "Base": Base}
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["async_session", "engine", "Base"]
