"""Admin endpointy — ochrana prístupu."""


def test_admin_logs_requires_auth(client):
    # Neprihlásený používateľ nesmie čítať logy.
    r = client.get("/api/admin/logs")
    assert r.status_code in (401, 403)


def test_admin_users_requires_auth(client):
    r = client.get("/api/admin/users")
    assert r.status_code in (401, 403)
