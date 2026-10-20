from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple

class BasePlatform(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass

    @abstractmethod
    def validate_gig(self, gig_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate gig data according to platform constraints."""
        pass

    @abstractmethod
    def validate_proposal(self, proposal_text: str) -> Tuple[bool, List[str]]:
        """Validate proposal according to platform guidelines."""
        pass

    @abstractmethod
    def get_seo_rules(self) -> Dict[str, Any]:
        """Returns platform-specific SEO ranking weights and constraints."""
        pass

    @abstractmethod
    def format_gig_markdown(self, gig_data: Dict[str, Any]) -> str:
        """Formats gig data into clean readable markdown for review."""
        pass
