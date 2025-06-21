from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from ..deps import SessionDep, get_current_username
from ..models.models import (
    BlocCategory,
    BlocCategoryCreate,
    BlocCategoryUpdate,
    BlocCategoryRead,
)
from ..security import verify_exists_and_owns

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[BlocCategoryRead])
def get_categories(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> list[BlocCategoryRead]:
    categories = session.exec(select(BlocCategory).filter(BlocCategory.user == current_user))
    return [BlocCategoryRead.serialize(category) for category in categories]


@router.post("", response_model=BlocCategoryRead)
def post_category(
    category: BlocCategoryCreate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> BlocCategoryRead:
    weight = category.weight
    if weight is None:
        max_weight = session.exec(
            select(func.max(BlocCategory.weight)).where(BlocCategory.user == current_user)
        ).one()
        weight = (max_weight or 0) + 1

    new_category = BlocCategory(
        name=category.name,
        color=category.color,
        weight=weight,
        user=current_user,
    )
    session.add(new_category)
    session.commit()
    session.refresh(new_category)
    return BlocCategoryRead.serialize(new_category)


@router.put("/{category_id}", response_model=BlocCategoryRead)
def put_category(
    session: SessionDep,
    category_id: int,
    category: BlocCategoryUpdate,
    current_user: Annotated[str, Depends(get_current_username)],
) -> BlocCategoryRead:
    db_category = session.get(BlocCategory, category_id)
    verify_exists_and_owns(current_user, db_category)

    category_data = category.model_dump(exclude_unset=True)
    for key, value in category_data.items():
        setattr(db_category, key, value)

    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return BlocCategoryRead.serialize(db_category)


@router.delete("/{category_id}")
def delete_category(
    session: SessionDep,
    category_id: int,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_category = session.get(BlocCategory, category_id)
    verify_exists_and_owns(current_user, db_category)

    if get_category_blocs_cnt(session, category_id, current_user) > 0:
        raise HTTPException(status_code=409, detail="The resource already exists")

    session.delete(db_category)
    session.commit()
    return {}


@router.get("/{category_id}/count")
def get_category_blocs_cnt(
    session: SessionDep,
    category_id: int,
    current_user: Annotated[str, Depends(get_current_username)],
) -> int:
    db_category = session.get(BlocCategory, category_id)
    verify_exists_and_owns(current_user, db_category)
    return len(db_category.blocs) + len(db_category.programblocs)
