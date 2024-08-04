from fastapi import APIRouter

from src.config.app_config import get_settings
from src.dtos.schema_in.user import UserCreate
from src.dtos.schema_out.bot import BotOut
from src.dtos.schema_out.user import UserOut
from src.services.bot_service import BotService

settings = get_settings()

admin_bot_router = APIRouter()

from math import ceil
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.config.app_config import get_settings
from src.models.all_models import User
from src.security import get_current_user_admin
from src.services.user_service import UserService

settings = get_settings()
user_router = APIRouter()
admin_user_router = APIRouter()


@admin_user_router.post('/create', summary="Create new user", status_code=201, response_model=UserOut)
async def create_user(data: UserCreate, user: User = Depends(get_current_user_admin)):
    return await UserService.create_user(data)


@admin_user_router.get('/search', summary='Enhanced search for users with advanced pagination info',
                       response_model=dict)
async def search_users(
        search_by: Optional[str] = Query(None, pattern="^(email|username|first_name|last_name)$"),
        search_value: Optional[str] = None,
        page: int = Query(1, ge=1),  # Changed from page_id to page
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("_id", pattern="^(_id|email|username|created_at)$"),
        sort_order: str = Query("asc", pattern="^(asc|desc)$"),
        current_user: User = Depends(get_current_user_admin)
):
    skip = (page - 1) * limit  # Calculate skip based on page number

    users, total = await UserService.search_users(
        search_by=search_by,
        search_value=search_value,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )

    total_pages = ceil(total / limit)
    has_next = page < total_pages
    has_previous = page > 1

    response_data = {
        "users": [user.json_encode() for user in users],
        "pagination": {
            "total": total,
            "total_pages": total_pages,
            "limit": limit,
            "current_page": page,
            "has_next": has_next,
            "has_previous": has_previous,
        }
    }

    return JSONResponse(content=response_data)


@admin_user_router.get('/{id}', summary='Get user by ID', response_model=UserOut)
async def get_user(id: UUID, user: User = Depends(get_current_user_admin)):
    user = await UserService.get_user_by_id_role(id)
    return user


@admin_user_router.get('', summary='Get all users', response_model=List[UserOut])
async def get_all_users(user: User = Depends(get_current_user_admin)):
    users = await UserService.get_all_users()
    return users


@admin_bot_router.get('/users/{id}', summary='Get bot by ID', response_model=List[BotOut])
async def get_bots_user(id: UUID, user: User = Depends(get_current_user_admin)):
    return await BotService.get_bots_by_user_id(id)


@admin_bot_router.get('', summary='Get bot by ID', response_model=List[BotOut])
async def get_bots(user: User = Depends(get_current_user_admin)):
    return await BotService.get_all_bots()


@admin_bot_router.get('/bots/search', summary='Enhanced search for users with advanced pagination info',
                      response_model=dict)
async def search_bots(
        search_by: Optional[str] = Query(None, pattern="^(email|username|first_name|last_name)$"),
        search_value: Optional[str] = None,
        page: int = Query(1, ge=1),  # Changed from page_id to page
        limit: int = Query(10, ge=1, le=100),
        sort_by: str = Query("_id", pattern="^(_id|email|username|created_at)$"),
        sort_order: str = Query("asc", pattern="^(asc|desc)$"),
        current_user: User = Depends(get_current_user_admin)
):
    skip = (page - 1) * limit  # Calculate skip based on page number

    users, total = await BotService.search_bots(
        search_by=search_by,
        search_value=search_value,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )

    total_pages = ceil(total / limit)
    has_next = page < total_pages
    has_previous = page > 1

    response_data = {
        "users": [user.json_encode() for user in users],
        "pagination": {
            "total": total,
            "total_pages": total_pages,
            "limit": limit,
            "current_page": page,
            "has_next": has_next,
            "has_previous": has_previous,
        }
    }

    return JSONResponse(content=response_data)
