from app.api.deps import get_current_user, get_db
from app.domain.user import User
from app.schemas.rooms import RoomCreateRequest, RoomListItem, RoomListResponse
from app.services.room_service import RoomService
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=RoomListResponse)
def list_rooms(db: Session = Depends(get_db)) -> RoomListResponse:
    service = RoomService(db)
    items = [RoomListItem.model_validate(room) for room in service.list_rooms()]
    return RoomListResponse(items=items)


@router.post("", response_model=RoomListItem, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomListItem:
    service = RoomService(db)
    room, _created = service.create_room(name=payload.name, actor_id=current_user.id)
    return RoomListItem.model_validate(room)
