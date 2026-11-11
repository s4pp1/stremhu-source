"""Commit-owned cache actions; Session.info retains only plain scope snapshots."""

from dataclasses import dataclass

from sqlalchemy import event
from sqlalchemy.orm import Session, SessionTransaction

from app.common.logger import logger

_DIRTY = "stremhu_stream_cache_dirty"
_SAVEPOINTS = "stremhu_stream_cache_savepoints"


@dataclass
class _SavepointScope:
    transaction_id: int
    present: bool
    scope: set[str] | None
    committed: bool = False


def mark_stream_cache_dirty(db: Session, user_id: str | None = None) -> None:
    if user_id is None:
        db.info[_DIRTY] = None
    elif _DIRTY not in db.info:
        db.info[_DIRTY] = {user_id}
    elif db.info[_DIRTY] is not None:
        db.info[_DIRTY].add(user_id)
        if len(db.info[_DIRTY]) > 1024:
            db.info[_DIRTY] = None


@event.listens_for(Session, "after_transaction_create")
def _snapshot_savepoint_scope(db: Session, transaction: SessionTransaction) -> None:
    if transaction.nested:
        scope = db.info.get(_DIRTY)
        frames = db.info.setdefault(_SAVEPOINTS, [])
        frames.append(_SavepointScope(id(transaction), _DIRTY in db.info, set(scope) if scope is not None else None))


@event.listens_for(Session, "after_commit")
def _note_successful_savepoint(db: Session) -> None:
    # This event never drains actions. Only the explicit outer owner does that.
    transaction = db.get_nested_transaction()
    for frame in db.info.get(_SAVEPOINTS, []):
        if transaction is not None and frame.transaction_id == id(transaction):
            frame.committed = True


@event.listens_for(Session, "after_transaction_end")
def _restore_rolled_back_savepoint(db: Session, transaction: SessionTransaction) -> None:
    if not transaction.nested:
        return
    frames = db.info.get(_SAVEPOINTS, [])
    if frames and frames[-1].transaction_id == id(transaction):
        frame = frames.pop()
        if not frame.committed:
            if frame.present:
                db.info[_DIRTY] = frame.scope
            else:
                db.info.pop(_DIRTY, None)


@event.listens_for(Session, "after_soft_rollback")
def _discard_outer_rollback(db: Session, transaction: SessionTransaction) -> None:
    if transaction.parent is None:
        discard_commit_actions(db)


def discard_commit_actions(db: Session) -> None:
    db.info.pop(_DIRTY, None)
    db.info.pop(_SAVEPOINTS, None)


def _invalidate_scope(scope: set[str] | None) -> None:
    from app.modules.stremio.service import invalidate_stream_cache

    if scope is None:
        invalidate_stream_cache()
    else:
        for user_id in scope:
            invalidate_stream_cache(user_id)


def drain_commit_actions(db: Session) -> None:
    if _DIRTY not in db.info:
        return
    scope = db.info.pop(_DIRTY)
    try:
        _invalidate_scope(scope)
    except Exception as error:
        logger.error("operation=post-commit-cache-invalidation kind=%s fallback=global", type(error).__name__)
        try:
            _invalidate_scope(None)
        except Exception:
            raise RuntimeError("Committed database write; cache invalidation failed.") from None


def commit_session(db: Session) -> None:
    try:
        db.commit()
    except BaseException:
        try:
            db.rollback()
        finally:
            discard_commit_actions(db)
        raise
    # A post-commit failure must not be reported as a failed DB commit/rollback.
    drain_commit_actions(db)
