from app.models import SessionVideo, VideoFile, ViewType


def test_replace_session_video_updates_existing_binding(
    client,
    auth_headers,
    db_session,
    test_session,
    test_session_video,
):
    replacement = VideoFile(
        original_filename="replacement.mp4",
        stored_filename="replacement_stored.mp4",
        storage_path="/tmp/replacement.mp4",
        mime_type="video/mp4",
        size_bytes=2048,
        checksum_sha256="replacement-checksum",
    )
    db_session.add(replacement)
    db_session.flush()

    response = client.put(
        f"/api/v1/sessions/{test_session.id}/videos/{test_session_video.id}",
        json={
            "video_file_id": replacement.id,
            "view_type": "side",
            "fps": 50.0,
            "resolution": "1920x1080",
            "sync_offset_ms": 12,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == test_session_video.id
    assert body["video_file_id"] == replacement.id
    assert body["video"]["original_filename"] == "replacement.mp4"
    assert body["fps"] == 50.0
    assert body["sync_offset_ms"] == 12

    links = db_session.query(SessionVideo).filter(SessionVideo.session_id == test_session.id).all()
    assert len(links) == 1
    assert links[0].video_file_id == replacement.id
    assert links[0].view_type == ViewType.SIDE
