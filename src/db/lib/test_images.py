import logging
import os
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, SQLModel, col, create_engine, delete, select

from .content_models import ImageInfo, ImagesUserSettings, UserImageView
from .images import (
    AllImagesAreShownException,
    add_images_from_folder,
    get_next_image,
    mark_image_as_seen,
    reset_images_user,
)

logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
# if os.environ.get("TEST_ENV") != "ci":
from dotenv import load_dotenv

load_dotenv(".env")


logging.basicConfig(level=logging.info)
logger = logging.getLogger(__name__)

# DATABASE_URL = f"sqlite:///imgs.sqlite"
DB_URL = os.environ.get("DB_URL")

engine = create_engine(DB_URL)

user_id = "43272691850341e9a957d25f4e667042"


@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
        # Cleanup
        session.rollback()
        # session.exec(delete(UserImageView))
        # session.exec(delete(UserSettings))
        # session.exec(delete(ImageInfo))
        # session.commit()
        # session.exec(delete(ImageInfo))
        # session.commit()


def test_smoke(session):
    assert True


@pytest.mark.skipif(
    os.environ.get("ENV", "") == "CI", reason="too hard to setup the environment automatically=("
)
def test_get_next_image(session):
    reset_images_user(session, user_id)
    i = 0
    with pytest.raises(AllImagesAreShownException):
        while True:
            res = get_next_image(
                session,
                user_id,
                430,
                requested_location="private massage room",
                requested_image_type="explicit",
            )
            if res is None:
                break
            mark_image_as_seen(session, user_id, res.id)
            logger.info(f"{i} {res.location}, {res.rating}")
            i += 1

    if i < 200:
        res = get_next_image(
            session,
            user_id,
            430,
            requested_location="private massage room",
            requested_image_type="explicit",
        )
        images = session.exec(select(ImageInfo).where(ImageInfo.character == 430)).all()
        subquery = select(UserImageView.image_id).where(UserImageView.user_id == user_id)
        print(len(images))
        subquery = select(UserImageView.image_id).where(UserImageView.user_id == user_id)

        missing_views = session.exec(
            select(ImageInfo).where(col(ImageInfo.id).not_in(subquery))
        ).all()
        print(len(missing_views), list(map(lambda x: (x.location, x.rating), missing_views)))

    assert i > 200
    # assert i == img_cnt, f"Expected {img_cnt} images, got {i}"


@pytest.mark.skipif(
    os.environ.get("ENV", "") == "CI", reason="too hard to setup the environment automatically=("
)
def test_reset_user(session):
    # inserted, updated = add_images_from_folder(session, "lib/test/img/img")
    i = 0
    reset_images_user(session, user_id)
    with pytest.raises(AllImagesAreShownException):
        while True:
            res = get_next_image(
                session,
                user_id,
                430,
                requested_location="private massage room",
                requested_image_type="explicit",
            )
            if res is None:
                break
            mark_image_as_seen(session, user_id, res.id)
            logger.info(f"{i} {res.location}, {res.rating}")
            i += 1

    reset_images_user(session, user_id)

    user = session.get(ImagesUserSettings, user_id)
    assert user == None
    j = 0
    with pytest.raises(AllImagesAreShownException):
        while True:
            res = get_next_image(
                session,
                user_id,
                430,
                requested_location="private massage room",
                requested_image_type="explicit",
            )
            if res is None:
                break
            mark_image_as_seen(session, user_id, res.id)
            logger.info(f"{j} {res.location}, {res.rating}")
            j += 1

    assert i == j
    assert i > 0


# def test_get_next_image2(session):
#     # reset_images_user(session, user_id)
#     for _ in range(10):
#         fi = get_next_image(session, user_id, 21, "nude")
#         # print(fi)
#         mark_image_as_seen(session, user_id, fi.id)
#         # si = get_next_image(session, user_id, 1, "explicit")
#         session.commit()
#     # assert si.rating == "nude"
