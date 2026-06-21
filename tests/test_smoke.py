"""Phase 0 smoke tests: the project boots and the home page renders."""


def test_truth():
    assert 1 + 1 == 2


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Course Folder Management System" in response.content
