import asyncio

from app.services.auth.supabase_service import SupabaseAuthService


class FakeSupabaseIntegration:
    enabled = True

    async def verify_token(self, token):
        return {"token": token}

    def extract_user_info(self, payload):
        return {
            "supabase_user_id": "supabase_new",
            "email": "student@example.com",
            "email_verified": True,
            "name": "Student",
            "picture": "",
        }


class FakeUserRepository:
    _db = object()

    def __init__(self):
        self.linked = None
        self.users = {
            "legacy_user": {
                "user_id": "legacy_user",
                "email": "student@example.com",
                "auth_provider": "legacy_google",
            }
        }

    async def find_by_supabase_id(self, supabase_user_id):
        return None

    async def find_by_email(self, email):
        return self.users["legacy_user"] if email == "student@example.com" else None

    async def link_supabase_identity(self, user_id, supabase_user_id):
        self.linked = (user_id, supabase_user_id)
        self.users[user_id]["auth_provider"] = "supabase"
        self.users[user_id]["supabase_user_id"] = supabase_user_id

    async def find_by_user_id(self, user_id):
        return self.users.get(user_id)

    async def create_supabase_user(self, **kwargs):
        raise AssertionError("verified same-email login should link legacy user")


def test_verified_same_email_supabase_login_reuses_internal_user_id():
    repo = FakeUserRepository()
    service = SupabaseAuthService(repo, FakeSupabaseIntegration())

    user = asyncio.run(service.authenticate("valid-token"))

    assert user["user_id"] == "legacy_user"
    assert user["supabase_user_id"] == "supabase_new"
    assert repo.linked == ("legacy_user", "supabase_new")
