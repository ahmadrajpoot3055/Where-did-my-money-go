from app.models.user import User, LoginHistory

def test_registration_success(client, app):
    res = client.post("/auth/register", data={
        "full_name": "Charlie Chaplin",
        "email": "charlie@test.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        u = User.query.filter_by(email="charlie@test.com").first()
        assert u is not None
        assert u.password_hash != "Password123!"
        assert u.preferences is not None

def test_registration_rejects_duplicate_email(client, app):
    res = client.post("/auth/register", data={
        "full_name": "Alice Clone",
        "email": "alice@test.com", # already exists in conftest
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res.status_code == 200
    assert b"already exists" in res.data

def test_login_and_logout(client, app):
    # Success
    res = client.post("/auth/login", data={
        "email": "alice@test.com",
        "password": "Pass123!"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back" in res.data or b"Dashboard" in res.data

    with app.app_context():
        lh = LoginHistory.query.filter_by(user_id=1, event_type="Success").first()
        assert lh is not None

    # Logout
    res = client.post("/auth/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"signed out" in res.data

def test_user_ownership_isolation(auth_client):
    # Alice (id 1) tries to edit Bob's account (id 2) -> Should receive 403 Forbidden
    res = auth_client.get("/accounts/2/edit")
    assert res.status_code == 403

