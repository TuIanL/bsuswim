import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
from alembic.config import Config
from alembic import command

from app.main import app
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.models import User, TrainingSession, Athlete
from app.models.annotation import AnnotationFile, AnnotationFileStatus, AnnotationSource
from app.models.video import SessionVideo, VideoFile, ViewType
from app.models.normalized_annotation import NormalizedAnnotation

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or get_settings().database_url


@pytest.fixture(scope="session")
def engine():
    e = create_engine(DATABASE_URL)
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(alembic_cfg, "head")
    yield e
    command.downgrade(alembic_cfg, "base")


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()

    app.dependency_overrides[get_db] = lambda: session
    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def test_coach(db_session: Session) -> User:
    coach = User(
        username="test_coach",
        email="coach@test.com",
        full_name="Test Coach",
        role="coach",
        password_hash="dummy",
        is_active=True,
    )
    db_session.add(coach)
    db_session.flush()
    return coach


@pytest.fixture
def auth_headers(test_coach):
    app.dependency_overrides[get_current_user] = lambda: test_coach
    yield {}
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def test_athlete(db_session: Session, test_coach: User) -> Athlete:
    athlete = Athlete(name="Test Athlete", coach_id=test_coach.id)
    db_session.add(athlete)
    db_session.flush()
    return athlete


@pytest.fixture
def test_session(db_session: Session, test_coach: User, test_athlete: Athlete) -> TrainingSession:
    ts = TrainingSession(
        athlete_id=test_athlete.id,
        coach_id=test_coach.id,
        title="Test Session",
        stroke_type="freestyle",
    )
    db_session.add(ts)
    db_session.flush()
    return ts


@pytest.fixture
def test_video_file(db_session: Session) -> VideoFile:
    vf = VideoFile(
        original_filename="test.mp4",
        stored_filename="test_stored.mp4",
        storage_path="/tmp/test.mp4",
        mime_type="video/mp4",
        size_bytes=1024,
        checksum_sha256="abc123",
    )
    db_session.add(vf)
    db_session.flush()
    return vf


@pytest.fixture
def test_session_video(db_session: Session, test_session: TrainingSession, test_video_file: VideoFile) -> SessionVideo:
    sv = SessionVideo(
        session_id=test_session.id,
        video_file_id=test_video_file.id,
        view_type=ViewType.SIDE,
        fps=60.0,
    )
    db_session.add(sv)
    db_session.flush()
    return sv


@pytest.fixture
def test_normalized_annotation(db_session: Session, test_session_video: SessionVideo) -> NormalizedAnnotation:
    """侧视角 COCO17 合成标注，供 side_2d_kinematics API/持久化测试。"""
    from fixtures.synthetic_kinematics import build_synthetic_annotation

    ann = build_synthetic_annotation(96)
    record = NormalizedAnnotation(
        session_video_id=test_session_video.id,
        revision=1,
        schema_version="swim-annotation.v1",
        source="cvat",
        fps=ann["fps"],
        frame_count=len(ann["keypoint_frames"]),
        scale=ann["scale"],
        keypoint_frames=ann["keypoint_frames"],
        annotation_metadata={"stroke_type": "freestyle"},
        swim_direction=ann["swim_direction"],
    )
    db_session.add(record)
    db_session.flush()
    return record


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as requiring a real database")
