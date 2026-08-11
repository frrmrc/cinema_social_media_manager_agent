from social_media_manager_agent.schemas import Post
from social_media_manager_agent.tools.storage import save_post


def test_save_post_writes_json_file(tmp_path):
    post = Post(title="Zootropolis 2: back in theaters!", body="...", style="Informative",
                publish_at="2025-12-01T10:00:00")

    path = save_post(post, save_folder=tmp_path)

    assert path.exists()
    assert "Zootropolis" in path.read_text(encoding="utf-8")


def test_save_post_sanitizes_special_characters(tmp_path):
    post = Post(title="Movie: 'Special'?!", body="...", style="Teaser", publish_at="2025-12-01T10:00:00")

    path = save_post(post, save_folder=tmp_path)

    assert path.exists()
    assert ":" not in path.name and "'" not in path.name