import json

from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.entities import (
    EntityCommandRequest,
    EntityCommandResponse,
    EntityListItem,
    EntityListResponse,
    EntityStateListItem,
    EntityStateListResponse,
    EntityStateResponse,
    EntityStateUpdateRequest,
)
from app.services.command_service import CommandService
from app.services.entity_service import EntityService
from app.services.entity_state_service import EntityStateService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=EntityListResponse)
def list_entities(db: Session = Depends(get_db)) -> EntityListResponse:
    service = EntityService(db)
    items = [EntityListItem.model_validate(entity) for entity in service.list_entities()]
    return EntityListResponse(items=items)


@router.get("/states", response_model=EntityStateListResponse)
def list_entity_states(db: Session = Depends(get_db)) -> EntityStateListResponse:
    service = EntityService(db)
    items = []
    for entity_id, state in service.list_states():
        if state is None:
            continue
        items.append(
            EntityStateListItem(
                entity_id=entity_id,
                value=json.loads(state.value_json),
                source=state.source,
                updated_at=state.updated_at,
                version=state.version,
            )
        )
    return EntityStateListResponse(items=items)


@router.get("/{entity_id}/state", response_model=EntityStateResponse)
def get_entity_state(entity_id: str, db: Session = Depends(get_db)) -> EntityStateResponse:
    state = EntityStateService(db).get_state(entity_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity state not found")
    return EntityStateResponse(
        entity_id=state.entity_id,
        value=json.loads(state.value_json),
        source=state.source,
        updated_at=state.updated_at,
        version=state.version,
    )


@router.put("/{entity_id}/state", response_model=EntityStateResponse)
def put_entity_state(
    entity_id: str,
    payload: EntityStateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntityStateResponse:
    try:
        state = EntityStateService(db).set_state(
            entity_id=entity_id,
            value=payload.value,
            source=payload.source,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return EntityStateResponse(
        entity_id=state.entity_id,
        value=json.loads(state.value_json),
        source=state.source,
        updated_at=state.updated_at,
        version=state.version,
    )


@router.post("/{entity_id}/commands", response_model=EntityCommandResponse)
def post_entity_command(
    entity_id: str,
    payload: EntityCommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntityCommandResponse:
    try:
        result = CommandService(db).execute_entity_command(
            entity_id=entity_id,
            command=payload.command,
            params=payload.params,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return EntityCommandResponse.model_validate(result)
