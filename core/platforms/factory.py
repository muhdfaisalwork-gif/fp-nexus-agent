from typing import Optional
from .base import BasePlatform
from .fiverr import FiverrPlatform
from .upwork import UpworkPlatform
from .freelancer import FreelancerPlatform

class PlatformFactory:
    _platforms = {
        "fiverr": FiverrPlatform,
        "upwork": UpworkPlatform,
        "freelancer": FreelancerPlatform,
        "freelancer.com": FreelancerPlatform,
        "contra": UpworkPlatform,
        "catalog": UpworkPlatform,
        "buyer_request": FiverrPlatform
    }

    @classmethod
    def get_platform(cls, platform_name: Optional[str] = None) -> BasePlatform:
        name = (platform_name or "fiverr").lower().strip()
        platform_cls = cls._platforms.get(name, FiverrPlatform)
        return platform_cls()

    @classmethod
    def list_supported_platforms(cls) -> list:
        return list(cls._platforms.keys())
