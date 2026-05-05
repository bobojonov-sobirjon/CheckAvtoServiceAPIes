"""
Accounts API views package.

Currently re-exports legacy views for compatibility.
Gradually move view classes from apps.accounts.views into this package.
"""

from apps.accounts.views import *  # noqa: F401,F403

