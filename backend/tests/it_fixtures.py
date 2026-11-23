import pytest
from sqlalchemy import delete, select

from app.models.it_request import (
    AccessCatalog,
    ITRequest,
    ITWorkflowTelemetry,
    RequestApproval,
    RequestEntity,
    RequestEvent,
    Runbook,
    RunbookExecution,
    SoftwareCatalog,
)
from app.models.it_request import ITRiskLevel
from tests.ai_fixtures import model_by_key


RUNBOOKS = [
    ("software.install.vscode", "software_install", ITRiskLevel.LOW, True),
    ("software.install.python", "software_install", ITRiskLevel.LOW, True),
    ("software.install.git", "software_install", ITRiskLevel.LOW, True),
    ("software.install.visio", "software_install", ITRiskLevel.MEDIUM, True),
    ("access.request.jira", "access_grant", ITRiskLevel.MEDIUM, True),
    ("access.request.confluence", "access_grant", ITRiskLevel.LOW, True),
    ("access.request.finance_shared_drive", "access_grant", ITRiskLevel.HIGH, True),
    ("access.privileged.blocked", "privileged_access", ITRiskLevel.CRITICAL, False),
]


@pytest.fixture
async def it_catalogs():
    from app.core.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        for runbook_id, action_type, risk, rollback in RUNBOOKS:
            existing = await session.scalar(select(Runbook).where(Runbook.id == runbook_id))
            if existing is None:
                session.add(
                    Runbook(
                        id=runbook_id,
                        name=runbook_id,
                        version="1",
                        action_type=action_type,
                        enabled=True,
                        risk_level=risk,
                        rollback_supported=rollback,
                    )
                )
        await session.flush()

        async def add_software(**kwargs):
            found = await session.scalar(
                select(SoftwareCatalog).where(SoftwareCatalog.name == kwargs["name"])
            )
            if found is None:
                session.add(SoftwareCatalog(enabled=True, **kwargs))

        await add_software(
            name="Visual Studio Code",
            vendor="Microsoft",
            version="latest",
            package_identifier="vscode",
            risk_level=ITRiskLevel.LOW,
            approval_required=False,
            runbook_id="software.install.vscode",
            aliases=["vscode", "vs code", "visual studio code"],
        )
        await add_software(
            name="Microsoft Visio",
            vendor="Microsoft",
            version="latest",
            package_identifier="visio",
            risk_level=ITRiskLevel.MEDIUM,
            approval_required=True,
            runbook_id="software.install.visio",
            aliases=["visio", "microsoft visio"],
        )
        found = await session.scalar(select(AccessCatalog).where(AccessCatalog.resource_name == "Jira"))
        if found is None:
            session.add(
                AccessCatalog(
                    resource_name="Jira",
                    resource_type="application",
                    environment="corporate",
                    risk_level=ITRiskLevel.MEDIUM,
                    approval_required=True,
                    enabled=True,
                    runbook_id="access.request.jira",
                    aliases=["jira"],
                )
            )
        found = await session.scalar(
            select(AccessCatalog).where(AccessCatalog.resource_name == "Finance Shared Drive")
        )
        if found is None:
            session.add(
                AccessCatalog(
                    resource_name="Finance Shared Drive",
                    resource_type="file_share",
                    environment="corporate",
                    risk_level=ITRiskLevel.HIGH,
                    approval_required=True,
                    enabled=True,
                    runbook_id="access.request.finance_shared_drive",
                    aliases=["finance shared drive"],
                )
            )
        await session.commit()
    yield
    async with session_factory() as session:
        await session.execute(delete(ITWorkflowTelemetry))
        await session.execute(delete(RequestEvent))
        await session.execute(delete(RunbookExecution))
        await session.execute(delete(RequestApproval))
        await session.execute(delete(RequestEntity))
        await session.execute(delete(ITRequest))
        await session.commit()
