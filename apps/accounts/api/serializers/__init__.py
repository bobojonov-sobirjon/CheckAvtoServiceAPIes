"""
Accounts API serializers package.

Currently re-exports legacy serializers for compatibility.
Gradually move serializers from apps.accounts.serializers into this package.
"""

from apps.accounts.serializers import *  # noqa: F401,F403

