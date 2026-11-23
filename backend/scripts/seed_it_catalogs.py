"""Seed allow-listed runbooks and demo catalogs. No real software is installed."""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.it_request import AccessCatalog, ITRiskLevel, Runbook, SoftwareCatalog

RUNBOOKS = [
    {
        "id": "software.install.vscode",
        "name": "Install Visual Studio Code",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.LOW,
        "description": "Simulated VS Code install runbook",
        "rollback_supported": True,
    },
    {
        "id": "software.install.python",
        "name": "Install Python",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.LOW,
        "description": "Simulated Python install runbook",
        "rollback_supported": True,
    },
    {
        "id": "software.install.git",
        "name": "Install Git",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.LOW,
        "description": "Simulated Git install runbook",
        "rollback_supported": True,
    },
    {
        "id": "software.install.7zip",
        "name": "Install 7-Zip",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.LOW,
        "description": "Simulated 7-Zip install runbook",
        "rollback_supported": True,
    },
    {
        "id": "software.install.visio",
        "name": "Install Microsoft Visio",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.MEDIUM,
        "description": "Simulated Visio install runbook requiring approval",
        "rollback_supported": True,
    },
    {
        "id": "software.install.office",
        "name": "Install Microsoft Office",
        "action_type": "software_install",
        "risk_level": ITRiskLevel.MEDIUM,
        "description": "Simulated Office install runbook requiring approval",
        "rollback_supported": True,
    },
    {
        "id": "access.request.jira",
        "name": "Grant Jira access",
        "action_type": "access_grant",
        "risk_level": ITRiskLevel.MEDIUM,
        "description": "Simulated Jira access grant",
        "rollback_supported": True,
    },
    {
        "id": "access.request.confluence",
        "name": "Grant Confluence access",
        "action_type": "access_grant",
        "risk_level": ITRiskLevel.LOW,
        "description": "Simulated Confluence access grant",
        "rollback_supported": True,
    },
    {
        "id": "access.request.finance_shared_drive",
        "name": "Grant Finance shared drive access",
        "action_type": "access_grant",
        "risk_level": ITRiskLevel.HIGH,
        "description": "Simulated finance drive access",
        "rollback_supported": True,
    },
    {
        "id": "access.request.monitoring_dashboard",
        "name": "Grant monitoring dashboard access",
        "action_type": "access_grant",
        "risk_level": ITRiskLevel.MEDIUM,
        "description": "Simulated monitoring dashboard access",
        "rollback_supported": True,
    },
    {
        "id": "access.privileged.blocked",
        "name": "Blocked privileged access",
        "action_type": "privileged_access",
        "risk_level": ITRiskLevel.CRITICAL,
        "description": "Placeholder; privileged access never auto-executes",
        "rollback_supported": False,
    },
]

SOFTWARE = [
    {
        "name": "Visual Studio Code",
        "vendor": "Microsoft",
        "version": "latest",
        "package_identifier": "vscode",
        "risk_level": ITRiskLevel.LOW,
        "approval_required": False,
        "runbook_id": "software.install.vscode",
        "aliases": ["vscode", "vs code", "visual studio code"],
    },
    {
        "name": "Python",
        "vendor": "Python Software Foundation",
        "version": "3.12",
        "package_identifier": "python",
        "risk_level": ITRiskLevel.LOW,
        "approval_required": False,
        "runbook_id": "software.install.python",
        "aliases": ["python", "python 3", "python 3.12"],
    },
    {
        "name": "Git",
        "vendor": "Git SCM",
        "version": "latest",
        "package_identifier": "git",
        "risk_level": ITRiskLevel.LOW,
        "approval_required": False,
        "runbook_id": "software.install.git",
        "aliases": ["git"],
    },
    {
        "name": "7-Zip",
        "vendor": "Igor Pavlov",
        "version": "latest",
        "package_identifier": "7zip",
        "risk_level": ITRiskLevel.LOW,
        "approval_required": False,
        "runbook_id": "software.install.7zip",
        "aliases": ["7zip", "7-zip"],
    },
    {
        "name": "Microsoft Visio",
        "vendor": "Microsoft",
        "version": "latest",
        "package_identifier": "visio",
        "risk_level": ITRiskLevel.MEDIUM,
        "approval_required": True,
        "runbook_id": "software.install.visio",
        "aliases": ["visio", "microsoft visio"],
    },
    {
        "name": "Microsoft Office",
        "vendor": "Microsoft",
        "version": "latest",
        "package_identifier": "office",
        "risk_level": ITRiskLevel.MEDIUM,
        "approval_required": True,
        "runbook_id": "software.install.office",
        "aliases": ["office", "microsoft office"],
    },
]

ACCESS = [
    {
        "resource_name": "Jira",
        "resource_type": "application",
        "environment": "corporate",
        "risk_level": ITRiskLevel.MEDIUM,
        "approval_required": True,
        "runbook_id": "access.request.jira",
        "aliases": ["jira"],
    },
    {
        "resource_name": "Confluence",
        "resource_type": "application",
        "environment": "corporate",
        "risk_level": ITRiskLevel.LOW,
        "approval_required": False,
        "runbook_id": "access.request.confluence",
        "aliases": ["confluence"],
    },
    {
        "resource_name": "Finance Shared Drive",
        "resource_type": "file_share",
        "environment": "corporate",
        "risk_level": ITRiskLevel.HIGH,
        "approval_required": True,
        "runbook_id": "access.request.finance_shared_drive",
        "aliases": ["finance shared drive", "finance drive"],
    },
    {
        "resource_name": "Internal Monitoring Dashboard",
        "resource_type": "dashboard",
        "environment": "corporate",
        "risk_level": ITRiskLevel.MEDIUM,
        "approval_required": True,
        "runbook_id": "access.request.monitoring_dashboard",
        "aliases": ["monitoring dashboard", "internal monitoring"],
    },
]


async def seed() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        for spec in RUNBOOKS:
            existing = await session.scalar(select(Runbook).where(Runbook.id == spec["id"]))
            if existing is None:
                session.add(Runbook(enabled=True, version="1", **spec))
        await session.flush()

        for spec in SOFTWARE:
            existing = await session.scalar(
                select(SoftwareCatalog).where(SoftwareCatalog.package_identifier == spec["package_identifier"])
            )
            if existing is None:
                session.add(SoftwareCatalog(enabled=True, **spec))

        for spec in ACCESS:
            existing = await session.scalar(
                select(AccessCatalog).where(AccessCatalog.resource_name == spec["resource_name"])
            )
            if existing is None:
                session.add(AccessCatalog(enabled=True, **spec))
        await session.commit()
    print("IT catalogs and runbooks seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
