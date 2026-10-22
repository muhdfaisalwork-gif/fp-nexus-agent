from .gigs import router as gigs_router
from .proposals import router as proposals_router
from .seo import router as seo_router
from .inbox import router as inbox_router
from .competitors import router as competitors_router
from .brain import router as brain_router
from .profile import router as profile_router
from .settings import router as settings_router
from .reach import router as reach_router

__all__ = [
    "gigs_router",
    "proposals_router",
    "seo_router",
    "inbox_router",
    "competitors_router",
    "brain_router",
    "profile_router",
    "settings_router",
    "reach_router"
]
