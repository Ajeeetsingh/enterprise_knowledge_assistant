"""Role listing API endpoints (Admin only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.db.models import User
from app.dependencies import get_db
from app.schemas.roles import RoleListResponse, RoleResponse
from app.services import role_service

router = APIRouter()


@router.get("", response_model=RoleListResponse)
def list_roles_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_VIEW)),
) -> RoleListResponse:
    """List all available roles."""
    roles = role_service.list_roles(db)
    return RoleListResponse(roles=[RoleResponse.from_role(role) for role in roles])
