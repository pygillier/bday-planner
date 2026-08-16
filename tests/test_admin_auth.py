def test_dashboard_redirects_when_unauthenticated(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_login_page_renders(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "Pocket ID".encode() in response.data


def test_dashboard_reachable_with_session(client):
    with client.session_transaction() as session:
        session["admin_sub"] = "test-sub"
        session["admin_email"] = "admin@example.com"
    response = client.get("/admin/")
    assert response.status_code == 200
