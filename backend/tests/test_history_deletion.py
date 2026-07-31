from types import SimpleNamespace

from sqlalchemy import select

from app.models import AnalysisTask, AnalysisTaskStatus, SessionVideo, StorageCleanupFailure, TrainingSession, User
from app.services import history_deletion_service


def _use_upload_root(monkeypatch, upload_root):
    monkeypatch.setattr(
        history_deletion_service,
        "get_settings",
        lambda: SimpleNamespace(upload_dir=upload_root),
    )


def test_delete_owned_session_removes_orphan_video_file(
    client, auth_headers, db_session, test_session, test_video_file, test_session_video, tmp_path, monkeypatch
):
    _use_upload_root(monkeypatch, tmp_path)
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    test_video_file.storage_path = str(source)
    db_session.flush()

    response = client.delete(f"/api/v1/sessions/{test_session.id}", headers=auth_headers)

    assert response.status_code == 204
    assert db_session.get(TrainingSession, test_session.id) is None
    assert db_session.get(type(test_video_file), test_video_file.id) is None
    assert not source.exists()


def test_delete_keeps_video_shared_by_another_session(
    client, auth_headers, db_session, test_coach, test_athlete, test_session, test_video_file, test_session_video, tmp_path, monkeypatch
):
    _use_upload_root(monkeypatch, tmp_path)
    source = tmp_path / "shared.mp4"
    source.write_bytes(b"video")
    test_video_file.storage_path = str(source)
    other_session = TrainingSession(
        athlete_id=test_athlete.id, coach_id=test_coach.id, title="Other", stroke_type="freestyle"
    )
    db_session.add(other_session)
    db_session.flush()
    db_session.add(SessionVideo(session_id=other_session.id, video_file_id=test_video_file.id, view_type="side"))
    db_session.flush()

    response = client.delete(f"/api/v1/sessions/{test_session.id}", headers=auth_headers)

    assert response.status_code == 204
    assert db_session.get(type(test_video_file), test_video_file.id) is not None
    assert source.exists()


def test_delete_rejects_active_analysis_task(client, auth_headers, db_session, test_session):
    db_session.add(
        AnalysisTask(
            session_id=test_session.id,
            status=AnalysisTaskStatus.PROCESSING,
            request_payload={},
        )
    )
    db_session.flush()

    response = client.delete(f"/api/v1/sessions/{test_session.id}", headers=auth_headers)

    assert response.status_code == 409
    assert db_session.get(TrainingSession, test_session.id) is not None


def test_delete_rejects_path_outside_upload_root(
    client, auth_headers, db_session, test_session, test_video_file, test_session_video, tmp_path, monkeypatch
):
    _use_upload_root(monkeypatch, tmp_path)
    test_video_file.storage_path = "/tmp/not-owned.mp4"
    db_session.flush()

    response = client.delete(f"/api/v1/sessions/{test_session.id}", headers=auth_headers)

    assert response.status_code == 400
    assert db_session.get(TrainingSession, test_session.id) is not None


def test_delete_hides_another_coachs_session(client, auth_headers, db_session, test_athlete):
    other_coach = User(
        username="other_coach", email="other@example.com", password_hash="dummy", role="coach", is_active=True
    )
    db_session.add(other_coach)
    db_session.flush()
    other_session = TrainingSession(
        athlete_id=test_athlete.id, coach_id=other_coach.id, title="Other", stroke_type="freestyle"
    )
    db_session.add(other_session)
    db_session.flush()

    response = client.delete(f"/api/v1/sessions/{other_session.id}", headers=auth_headers)

    assert response.status_code == 404
    assert db_session.get(TrainingSession, other_session.id) is not None


def test_failed_file_cleanup_is_recorded_and_can_be_retried(
    client, auth_headers, db_session, test_session, test_video_file, test_session_video, tmp_path, monkeypatch
):
    _use_upload_root(monkeypatch, tmp_path)
    source = tmp_path / "retry.mp4"
    source.write_bytes(b"video")
    test_video_file.storage_path = str(source)
    db_session.flush()
    original_remove = history_deletion_service._remove_path
    monkeypatch.setattr(history_deletion_service, "_remove_path", lambda path: (_ for _ in ()).throw(OSError("locked")))

    response = client.delete(f"/api/v1/sessions/{test_session.id}", headers=auth_headers)

    assert response.status_code == 500
    failure = db_session.scalar(select(StorageCleanupFailure))
    assert failure is not None
    assert db_session.get(TrainingSession, test_session.id) is None

    monkeypatch.setattr(history_deletion_service, "_remove_path", original_remove)
    retry = client.post(f"/api/v1/sessions/cleanup-failures/{failure.id}/retry", headers=auth_headers)
    assert retry.status_code == 200
    assert retry.json()["resolved"] is True
    assert not source.exists()
