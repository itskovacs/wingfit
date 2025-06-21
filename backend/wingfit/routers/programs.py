import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..deps import SessionDep, get_current_username
from ..models.models import (
    BlocCategory,
    Image,
    Program,
    ProgramCreate,
    ProgramRead,
    ProgramReadComplete,
    ProgramStep,
    ProgramStepBloc,
    ProgramStepBlocCreate,
    ProgramStepBlocRead,
    ProgramStepBlocUpdate,
    ProgramStepCreate,
    ProgramStepRead,
    ProgramStepUpdate,
    ProgramStepWithBlocsRead,
    ProgramUpdate,
)
from ..security import verify_exists_and_owns
from ..utils.file import remove_image, save_image, read_image
from ..utils.logging import app_logger
from ..utils.misc import b64img_decode, b64e

router = APIRouter(prefix="/api/programs", tags=["programs"])


@router.post("/upload")
async def upload_program(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    file: UploadFile = File(...),
) -> ProgramRead:
    if file.content_type != "application/json":
        raise HTTPException(status_code=415, detail="Resource format not supported")

    try:
        content = await file.read()
        data = json.loads(content)
        new_program = await import_program(session, current_user, data)
    except Exception as exc:
        app_logger.error(f"[upload_program][{current_user}] An error occured: {exc}")
        raise HTTPException(status_code=400, detail="400")

    session.commit()
    return ProgramRead.serialize(new_program)


async def import_program(session, current_user, data) -> Program:
    try:
        ProgramCreate(**data)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Resource cannot be processed")

    new_program = Program(
        name=data.get("name"),
        description=data.get("description"),
        user=current_user,
    )

    if data.get("image"):
        image_bytes = b64img_decode(data.get("image"))
        filename = save_image(image_bytes, 400)
        if not filename:
            app_logger.error(f"[import_program][{current_user}] Image saving error, check logs")
            raise HTTPException(status_code=400, detail="Bad request")

        image = Image(filename=filename, user=current_user)
        session.add(image)
        session.commit()
        session.refresh(image)
        new_program.image_id = image.id

    session.add(new_program)
    session.flush()

    for step in data.get("steps", []):
        new_step = ProgramStep(
            name=step.get("name", None),
            repeat=step.get("repeat", 0),
            program_id=new_program.id,
            user=current_user,
        )
        session.add(new_step)
        session.flush()

        for bloc in step.get("blocs", []):
            bloc_category_name = bloc.get("category", {}).get("name")
            category = session.exec(
                select(BlocCategory).filter(
                    BlocCategory.user == current_user, BlocCategory.name == bloc_category_name
                )
            ).first()
            if not category:
                raise HTTPException(status_code=404, detail="Unknown category in Program Blocs")

            new_bloc = ProgramStepBloc(
                content=bloc.get("content"),
                duration=bloc.get("duration"),
                next_in=bloc.get("next_in", 0),
                category_id=category.id,
                program_step_id=new_step.id,
                user=current_user,
            )
            session.add(new_bloc)

    return new_program


@router.get("/{program_id}/export")
async def export_program(
    program_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
):
    db_program = session.exec(
        select(Program)
        .where(Program.id == program_id, Program.user == current_user)
        .options(selectinload(Program.steps))
    ).first()
    if not db_program:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    data = db_program.dict()  # Use dict() instead of serialize to get a dict
    data["steps"] = [ProgramStepWithBlocsRead.serialize(step) for step in db_program.steps]
    im = session.exec(select(Image).where(Image.user == current_user, Image.id == data["image_id"])).first()
    data["image"] = b64e(await read_image(im.filename))
    return data


@router.get("", response_model=list[ProgramRead])
async def get_programs(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> list[ProgramRead]:
    programs = session.exec(select(Program).filter(Program.user == current_user))
    return [ProgramRead.serialize(program) for program in programs]


@router.post("", response_model=ProgramRead)
async def post_program(
    program_data: ProgramCreate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramRead:
    new_program = Program(name=program_data.name, user=current_user)

    if program_data.image_id:
        db_img = session.get(Image, program_data.image_id)
        verify_exists_and_owns(current_user, db_img)
        new_program.image_id = db_img.id

    if program_data.image:
        image_bytes = b64img_decode(program_data.image)
        filename = save_image(image_bytes, 400)
        if not filename:
            app_logger.error(f"[post_program][{current_user}] Image saving error, check logs")
            raise HTTPException(status_code=400, detail="Bad request")

        image = Image(filename=filename, user=current_user)
        session.add(image)
        session.commit()
        session.refresh(image)
        new_program.image_id = image.id

    session.add(new_program)
    session.commit()
    session.refresh(new_program)
    return ProgramRead.serialize(new_program)


@router.put("/{program_id}", response_model=ProgramRead)
async def put_program(
    program_id: int,
    program: ProgramUpdate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramRead:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    program_data = program.model_dump(exclude_unset=True)
    remove_previous_image = False

    if (
        program_data.get("image_id") and program.image_id != db_program.image_id
    ):  # If image_id and image_id is different as the one in DB
        db_img = session.get(Image, program.image_id)
        verify_exists_and_owns(current_user, db_img)
        program_data.pop("image", None)  # Ensure consistency
        remove_previous_image = True

    if program_data.get("image"):
        image_bytes = b64img_decode(program_data.get("image"))
        filename = save_image(image_bytes, 400)
        if not filename:
            app_logger.error(f"[put_program][{current_user}] Image saving error, check logs")
            raise HTTPException(status_code=400, detail="Bad request")

        image = Image(filename=filename, user=current_user)
        session.add(image)
        session.commit()
        session.refresh(image)

        remove_previous_image = True
        program_data.pop("image")
        program_data["image_id"] = image.id

    if remove_previous_image and db_program.image_id:
        old_image = session.get(Image, db_program.image_id)

        if old_image and len(old_image.programs) == 1:
            try:
                remove_image(old_image.filename)
                session.delete(old_image)
            except Exception as exc:
                app_logger.error(
                    f"[put_program][{current_user}] Exception during previous image deletion: {exc}"
                )

    session.refresh(db_program)

    for key, value in program_data.items():
        setattr(db_program, key, value)

    session.add(db_program)
    session.commit()
    session.refresh(db_program)
    return ProgramRead.serialize(db_program)


@router.delete("/{program_id}")
def delete_program(
    program_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    if db_program.image and len(db_program.image.programs) == 1:
        try:
            remove_image(db_program.image.filename)
            session.delete(db_program.image)
        except Exception as exc:
            app_logger.error(f"[delete_program][{current_user}] Exception during image deletion: {exc}")
            raise HTTPException(
                status_code=500,
                detail="Roses are red, violets are blue, if you're reading this, I'm sorry for you",
            )

    session.delete(db_program)
    session.commit()
    return {}


@router.get("/{program_id}", response_model=ProgramReadComplete)
def get_program(
    program_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramReadComplete:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)
    return ProgramReadComplete.serialize(db_program)


@router.get("/{program_id}/steps", response_model=list[ProgramStepWithBlocsRead])
def get_program_steps(
    program_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> list[ProgramStepWithBlocsRead]:
    steps = session.exec(
        select(ProgramStep).filter(ProgramStep.user == current_user, ProgramStep.program_id == program_id)
    )
    return [ProgramStepWithBlocsRead.serialize(step) for step in steps]


@router.post("/{program_id}/steps", response_model=ProgramStepRead)
def post_program_step(
    program_id: int,
    step_data: ProgramStepCreate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramStepRead:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    new_step = ProgramStep(
        name=step_data.name,
        repeat=step_data.repeat,
        program_id=program_id,
        user=current_user,
    )
    session.add(new_step)
    session.commit()
    session.refresh(new_step)
    return ProgramStepRead.serialize(new_step)


@router.put("/{program_id}/steps/{step_id}", response_model=ProgramStepRead)
def put_program_step(
    program_id: int,
    step_id: int,
    step_data: ProgramStepUpdate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramStepRead:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    db_program_step = session.get(ProgramStep, step_id)
    verify_exists_and_owns(current_user, db_program_step)

    if db_program_step.program_id != program_id:
        raise HTTPException(status_code=400, detail="Bad request")

    step_data = step_data.model_dump(exclude_unset=True)
    for key, value in step_data.items():
        setattr(db_program_step, key, value)

    session.add(db_program_step)
    session.commit()
    session.refresh(db_program_step)
    return ProgramStepRead.serialize(db_program_step)


@router.delete("/{program_id}/steps/{step_id}")
def delete_program_step(
    program_id: int,
    step_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    db_program_step = session.get(ProgramStep, step_id)
    verify_exists_and_owns(current_user, db_program_step)

    if db_program_step.program_id != program_id:
        raise HTTPException(status_code=400, detail="Bad request")

    session.delete(db_program_step)
    session.commit()
    return {}


@router.post("/{program_id}/steps/{step_id}/blocs", response_model=ProgramStepBlocRead)
def post_program_step_bloc(
    program_id: int,
    step_id: int,
    bloc_data: ProgramStepBlocCreate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramStepBlocRead:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    db_program_step = session.get(ProgramStep, step_id)
    verify_exists_and_owns(current_user, db_program_step)

    if db_program_step.program_id != program_id:
        raise HTTPException(status_code=400, detail="Bad request")

    if not bloc_data.category and not bloc_data.category_id:
        app_logger.error(f"[post_program_step_bloc][{current_user}] No Category provided")
        raise HTTPException(status_code=400, detail="Bad request")

    new_bloc = ProgramStepBloc(
        content=bloc_data.content,
        duration=bloc_data.duration,
        next_in=bloc_data.next_in,
        program_step_id=step_id,
        user=current_user,
    )

    # category_id prioritized
    if bloc_data.category_id:
        new_bloc.category_id = bloc_data.category_id

    # Else we retrieve category.id for bloc.category_id
    else:
        new_bloc.category_id = bloc_data.category.id

    session.add(new_bloc)
    session.commit()
    return ProgramStepBlocRead.serialize(new_bloc)


@router.put(
    "/{program_id}/steps/{step_id}/blocs/{bloc_id}",
    response_model=ProgramStepBlocRead,
)
def put_program_step_bloc(
    program_id: int,
    step_id: int,
    bloc_id: int,
    bloc_data: ProgramStepBlocUpdate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> ProgramStepBlocRead:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    db_program_step = session.get(ProgramStep, step_id)
    verify_exists_and_owns(current_user, db_program_step)

    if db_program_step.program_id != program_id:
        raise HTTPException(status_code=400, detail="Bad request")

    db_program_step_bloc = session.get(ProgramStepBloc, bloc_id)
    verify_exists_and_owns(current_user, db_program_step_bloc)

    if db_program_step_bloc.program_step_id != step_id:
        raise HTTPException(status_code=400, detail="Bad request")

    bloc_data = bloc_data.model_dump(exclude_unset=True)
    if bloc_data.get("category"):
        bloc_data["category_id"] = bloc_data.get("category").get("id")
        bloc_data.pop("category")

    for key, value in bloc_data.items():
        setattr(db_program_step_bloc, key, value)

    session.add(db_program_step_bloc)
    session.commit()
    session.refresh(db_program_step_bloc)
    return ProgramStepBlocRead.serialize(db_program_step_bloc)


@router.delete("/{program_id}/steps/{step_id}/blocs/{bloc_id}")
def delete_program_step_bloc(
    program_id: int,
    step_id: int,
    bloc_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_program = session.get(Program, program_id)
    verify_exists_and_owns(current_user, db_program)

    db_program_step = session.get(ProgramStep, step_id)
    verify_exists_and_owns(current_user, db_program_step)

    if db_program_step.program_id != program_id:
        raise HTTPException(status_code=400, detail="Bad request")

    db_program_step_bloc = session.get(ProgramStepBloc, bloc_id)
    verify_exists_and_owns(current_user, db_program_step_bloc)

    if db_program_step_bloc.program_step_id != step_id:
        raise HTTPException(status_code=400, detail="Bad request")

    session.delete(db_program_step_bloc)
    session.commit()
    return {}
