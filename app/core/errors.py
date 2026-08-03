class SinteseError(Exception):
    """Base de erros do domínio."""


class BudgetExceeded(SinteseError):
    """Custo projetado/real estourou o teto do job."""


class ComplianceBlock(SinteseError):
    """Render barrado por regra de compliance (fonte ausente, photoreal de evento real, etc.)."""


class ProviderTimeout(SinteseError):
    """Geração no provider não concluiu dentro do timeout de polling."""
