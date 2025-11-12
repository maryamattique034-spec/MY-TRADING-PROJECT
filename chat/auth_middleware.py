import logging

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_key):
    # Close old database connections to prevent chaos in async code
    close_old_connections()
    try:
        access_token = AccessToken(token_key)
        user_id = access_token.payload.get("user_id")
        logger.info(f"User ID: {user_id}")

        if user_id:
            user_id = int(user_id)
        User = get_user_model()
        return User.objects.get(id=user_id)
    except Exception as e:
        # InvalidToken or User.DoesNotExist
        logger.error(f"Token authentication failed: {e}")
        return AnonymousUser()


# We don't check token in middleware now, just mark as Anonymous initially
class TokenAuthMiddleware:
    """
    Middleware to attach a user object.
    Full token validation will be done inside consumer upon first message.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Close old DB connections to be safe in async context
        close_old_connections()
        # Initially mark all users as Anonymous
        scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)


# Wrap with AuthMiddlewareStack to still allow session/auth integration
def TokenAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(TokenAuthMiddleware(inner))
