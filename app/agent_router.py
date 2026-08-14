from collections.abc import Iterable

from app.agent_models import AgentAction, AgentDecision


class AgentRouter:
    """Route structured user intent into an allowed workflow."""

    def __init__(
        self,
        available_versions: dict[str, Iterable[str]],
    ) -> None:
        self.available_versions = {
            product.strip(): tuple(
                dict.fromkeys(
                    version.strip()
                    for version in versions
                    if version.strip()
                )
            )
            for product, versions in available_versions.items()
            if product.strip()
        }

    def route(
        self,
        product: str,
        requested_versions: Iterable[str],
        comparison_requested: bool = False,
    ) -> AgentDecision:
        """Create a validated decision from structured request state."""

        normalized_product = product.strip()

        if not normalized_product:
            raise ValueError("Product cannot be empty")

        if normalized_product not in self.available_versions:
            raise ValueError(
                f"Unknown product: {normalized_product}"
            )

        versions = tuple(
            dict.fromkeys(
                version.strip()
                for version in requested_versions
                if version.strip()
            )
        )

        self._validate_versions(
            product=normalized_product,
            versions=versions,
        )

        if not versions:
            available = ", ".join(
                self.available_versions[normalized_product]
            )

            return AgentDecision(
                action=AgentAction.CLARIFY_VERSION,
                product=normalized_product,
                versions=(),
                message=(
                    "Which documentation version should I use? "
                    f"Available versions: {available}."
                ),
            )

        if comparison_requested:
            if len(versions) < 2:
                return AgentDecision(
                    action=AgentAction.CLARIFY_VERSION,
                    product=normalized_product,
                    versions=(),
                    message=(
                        "A comparison requires at least two "
                        "documentation versions."
                    ),
                )

            return AgentDecision(
                action=AgentAction.COMPARE_VERSIONS,
                product=normalized_product,
                versions=versions,
            )

        if len(versions) > 1:
            return AgentDecision(
                action=AgentAction.CLARIFY_VERSION,
                product=normalized_product,
                versions=(),
                message=(
                    "Multiple versions were provided. Please select "
                    "one version or explicitly request a comparison."
                ),
            )

        return AgentDecision(
            action=AgentAction.ANSWER,
            product=normalized_product,
            versions=versions,
        )

    def _validate_versions(
        self,
        product: str,
        versions: tuple[str, ...],
    ) -> None:
        """Reject versions outside the configured product scope."""

        allowed_versions = set(
            self.available_versions[product]
        )

        unknown_versions = [
            version
            for version in versions
            if version not in allowed_versions
        ]

        if unknown_versions:
            unknown = ", ".join(unknown_versions)

            raise ValueError(
                f"Unknown version for {product}: {unknown}"
            )