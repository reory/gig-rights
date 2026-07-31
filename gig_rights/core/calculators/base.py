"""Abstract base class for statutory holiday entitlement calculators."""

from abc import ABC, abstractmethod

from gig_rights.core.models import CalculationResult, PayPeriod, Worker


class BaseHolidayCalculator(ABC):
    """Interface for statutory holdiay pay and hours calculations."""

    @abstractmethod
    def calculate(
        self, worker: Worker, current_period: PayPeriod, **kwargs
    ) -> CalculationResult:
        """Execute calculation and return audit-ready result with metadata."""
