from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from core.management_models import (
    AGENT_LIFECYCLE_STATES,
    OWNER_ROLE,
    PERMISSIONS,
    PROVIDER_IDS,
    ROLE_DEFAULT_PERMISSIONS,
    ROLE_IDS,
    AgentProfile,
)
from core.artifact_service import ArtifactService
from core.finding_service import FINDING_CONFIDENCE, FINDING_SEVERITIES, FindingService
from core.management_service import EmployeeSummary, ManagementService
from core.knowledge_service import KNOWLEDGE_STATUSES, SOURCE_AUTHORITIES, KnowledgeService
from core.provider_service import ProviderHealthService, ProviderProvisioningService, ProviderRegistry
from core.product_metrics_service import ProductMetricsService
from core.skill_progress_service import SkillProgressService
from core.skill_package_service import SkillPackageService
from core.standards_service import MANDATORY_LEVELS, STANDARD_AUTHORITIES, StandardsService
from gui.localization import permission_label, readiness_label, role_label, status_label, tr


STATUS_LABELS = {
    "DRAFT": "Р§РµСЂРЅРѕРІРёРє",
    "ACTIVE": "РђРєС‚РёРІРµРЅ",
    "SUSPENDED": "РџСЂРёРѕСЃС‚Р°РЅРѕРІР»РµРЅ",
    "DISABLED": "РћС‚РєР»СЋС‡РµРЅ",
    "ARCHIVED": "РђСЂС…РёРІ",
}

PROVIDER_LABELS = {
    "CODEX_CLI": "Codex CLI",
    "GEMINI_CLI": "Gemini CLI",
    "CLAUDE_CLI": "Claude CLI",
    "FUTURE_PROVIDER": "Р‘СѓРґСѓС‰РёР№ provider",
    "UNAVAILABLE": "РќРµ РЅР°СЃС‚СЂРѕРµРЅ",
}


class DirectorConsoleDialog(QDialog):
    def __init__(
        self,
        management_service: ManagementService,
        provider_registry: ProviderRegistry,
        provider_health_service: ProviderHealthService,
        provider_provisioning_service: ProviderProvisioningService,
        skill_progress_service: SkillProgressService | None = None,
        skill_package_service: SkillPackageService | None = None,
        knowledge_service: KnowledgeService | None = None,
        standards_service: StandardsService | None = None,
        artifact_service: ArtifactService | None = None,
        finding_service: FindingService | None = None,
        product_metrics_service: ProductMetricsService | None = None,
        language: str = "ru",
        avatar_dir: str | Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.management_service = management_service
        self.provider_registry = provider_registry
        self.provider_health_service = provider_health_service
        self.provider_provisioning_service = provider_provisioning_service
        self.skill_progress_service = skill_progress_service
        self.skill_package_service = skill_package_service
        self.knowledge_service = knowledge_service
        self.standards_service = standards_service
        self.artifact_service = artifact_service
        self.finding_service = finding_service
        self.product_metrics_service = product_metrics_service
        self.language = language
        self.avatar_dir = Path(avatar_dir) if avatar_dir else None
        self.setWindowTitle("РљРѕРјР°РЅРґР°")
        self.resize(1120, 760)
        self.tabs = QTabWidget()

        self.overview_tab = OverviewTab(management_service, provider_health_service, self)
        self.employee_tab = EmployeesTab(management_service, provider_health_service, provider_provisioning_service, language, self.avatar_dir, self)
        self.roles_tab = RolesTab(management_service, language, self)
        self.permissions_tab = PermissionsTab(management_service, language, self)
        self.providers_tab = ProvidersTab(provider_registry, provider_health_service, provider_provisioning_service, management_service, language, self)
        self.skills_tab = SkillProgressTab(skill_progress_service, skill_package_service, management_service, self)
        self.knowledge_tab = KnowledgeTab(knowledge_service, self)
        self.standards_tab = StandardsTab(standards_service, self)
        self.artifacts_tab = ArtifactsTab(artifact_service, self)
        self.findings_tab = FindingsTab(finding_service, self)
        self.diagnostics_tab = ProductDiagnosticsTab(product_metrics_service, self)
        self.audit_tab = AuditTab(management_service, language, self)

        self.tabs.addTab(self.overview_tab, tr(language, "overview"))
        self.tabs.addTab(self.employee_tab, tr(language, "employees"))
        self.tabs.addTab(self.roles_tab, tr(language, "roles"))
        self.tabs.addTab(self.permissions_tab, tr(language, "permissions"))
        self.tabs.addTab(self.providers_tab, tr(language, "providers"))
        self.tabs.addTab(self.skills_tab, "РќР°РІС‹РєРё")
        self.tabs.addTab(self.knowledge_tab, "Р—РЅР°РЅРёСЏ")
        self.tabs.addTab(self.standards_tab, "РЎС‚Р°РЅРґР°СЂС‚С‹")
        self.tabs.addTab(self.artifacts_tab, "РђСЂС‚РµС„Р°РєС‚С‹")
        self.tabs.addTab(self.findings_tab, "Findings")
        self.tabs.addTab(self.diagnostics_tab, "Р”РёР°РіРЅРѕСЃС‚РёРєР°")
        self.tabs.addTab(self.audit_tab, tr(language, "audit"))

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        header = QLabel(f"{tr(language, 'owner')}: ORGANIZATION_OWNER")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(close)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.overview_tab.refresh()
        self.employee_tab.refresh()
        self.roles_tab.refresh()
        self.permissions_tab.refresh()
        self.providers_tab.refresh()
        self.skills_tab.refresh()
        self.knowledge_tab.refresh()
        self.standards_tab.refresh()
        self.artifacts_tab.refresh()
        self.findings_tab.refresh()
        self.diagnostics_tab.refresh()
        self.audit_tab.refresh()


class OverviewTab(QWidget):
    def __init__(self, service: ManagementService, provider_health_service: ProviderHealthService, console: DirectorConsoleDialog) -> None:
        super().__init__()
        self.service = service
        self.provider_health_service = provider_health_service
        self.console = console
        self.grid = QGridLayout()
        self.recent = QTextEdit()
        self.recent.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addLayout(self.grid)
        layout.addWidget(QLabel("РџРѕСЃР»РµРґРЅРёРµ РґРµР№СЃС‚РІРёСЏ"))
        layout.addWidget(self.recent, 1)

    def refresh(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        employees = self.service.list_employees()
        counts = {state: len([item for item in employees if item.lifecycle_state == state]) for state in AGENT_LIFECYCLE_STATES}
        providers = [profile.provider_id for profile in self.provider_health_service.registry.profiles()]
        available = 0
        unavailable = 0
        for provider in providers:
            health = self.provider_health_service.latest_health(provider)
            status = health.health_status if health is not None else "UNKNOWN"
            if status == "READY":
                available += 1
            elif status in ("NOT_READY", "BLOCKED"):
                unavailable += 1
        cards = [
            ("РђРєС‚РёРІРЅС‹Рµ СЃРѕС‚СЂСѓРґРЅРёРєРё", counts.get("ACTIVE", 0)),
            ("РџСЂРёРѕСЃС‚Р°РЅРѕРІР»РµРЅС‹", counts.get("SUSPENDED", 0)),
            ("РћС‚РєР»СЋС‡РµРЅС‹", counts.get("DISABLED", 0)),
            ("РђСЂС…РёРІ", counts.get("ARCHIVED", 0)),
            ("РќР°СЃС‚СЂРѕРµРЅРЅС‹Рµ СЂРѕР»Рё", len(self.service.list_roles())),
            ("Provider РґРѕСЃС‚СѓРїРЅС‹", available),
            ("Provider РЅРµРґРѕСЃС‚СѓРїРЅС‹", unavailable),
            ("Р РёСЃРєРѕРІР°РЅРЅС‹Рµ РєРѕРЅС„РёРіСѓСЂР°С†РёРё", len([item for item in employees if item.warnings])),
            ("Р‘Р°Р·Р° РґР°РЅРЅС‹С…", "OK"),
            ("Management repository", "OK"),
        ]
        for index, (title, value) in enumerate(cards):
            card = QGroupBox(title)
            card_layout = QVBoxLayout(card)
            label = QLabel(str(value))
            label.setObjectName("pageTitle")
            card_layout.addWidget(label)
            self.grid.addWidget(card, index // 4, index % 4)
        events = self.service.list_audit_events()[-8:]
        lines = [f"{row['created_at']} | {row['actor']} | {row['action']} | {row['object_id']}" for row in events]
        self.recent.setPlainText("\n".join(lines) if lines else "Р”РµР№СЃС‚РІРёР№ РїРѕРєР° РЅРµС‚.")


class EmployeesTab(QWidget):
    def __init__(
        self,
        service: ManagementService,
        provider_health_service: ProviderHealthService,
        provider_provisioning_service: ProviderProvisioningService,
        language: str,
        avatar_dir: Path | None,
        console: DirectorConsoleDialog,
    ) -> None:
        super().__init__()
        self.service = service
        self.provider_health_service = provider_health_service
        self.provider_provisioning_service = provider_provisioning_service
        self.language = language
        self.avatar_dir = avatar_dir
        self.console = console
        self.employees: list[EmployeeSummary] = []

        self.status_filter = QComboBox()
        self.status_filter.addItem(tr(language, "all"), "ALL")
        for state in sorted(AGENT_LIFECYCLE_STATES):
            self.status_filter.addItem(status_label(language, state), state)
        self.role_filter = QComboBox()
        self.role_filter.addItem(tr(language, "all_roles"), "ALL")
        for role_id in sorted(ROLE_IDS):
            self.role_filter.addItem(role_label(language, role_id), role_id)
        self.provider_filter = QComboBox()
        self.provider_filter.addItem(tr(language, "all_providers"), "ALL")
        for provider_id in sorted(PROVIDER_IDS):
            self.provider_filter.addItem(PROVIDER_LABELS.get(provider_id, provider_id), provider_id)
        self.warning_filter = QCheckBox(tr(language, "warnings_only"))

        for widget in (self.status_filter, self.role_filter, self.provider_filter, self.warning_filter):
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.refresh)
            else:
                widget.stateChanged.connect(self.refresh)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "name"),
                tr(language, "agent_id"),
                tr(language, "status"),
                tr(language, "roles"),
                tr(language, "provider"),
                tr(language, "persona"),
                tr(language, "rights"),
                tr(language, "readiness"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        add = QPushButton(tr(language, "add_employee"))
        open_button = QPushButton(tr(language, "open"))
        edit = QPushButton(tr(language, "edit"))
        suspend = QPushButton(tr(language, "suspend"))
        reactivate = QPushButton(tr(language, "reactivate"))
        archive = QPushButton(tr(language, "archive"))
        add.clicked.connect(self.add_employee)
        open_button.clicked.connect(self._show_selected_detail)
        edit.clicked.connect(self.edit_employee)
        suspend.clicked.connect(lambda: self.lifecycle_action("SUSPENDED"))
        reactivate.clicked.connect(lambda: self.lifecycle_action("ACTIVE"))
        archive.clicked.connect(lambda: self.lifecycle_action("ARCHIVED"))

        filters = QHBoxLayout()
        filters.addWidget(self.status_filter)
        filters.addWidget(self.role_filter)
        filters.addWidget(self.provider_filter)
        filters.addWidget(self.warning_filter)
        filters.addStretch(1)

        actions = QHBoxLayout()
        for button in (add, open_button, edit, suspend, reactivate, archive):
            actions.addWidget(button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self.table, 2)
        layout.addLayout(actions)
        layout.addWidget(QLabel(tr(language, "employee_card")))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        employees = self.service.list_employees(self.status_filter.currentData())
        role = self.role_filter.currentData()
        provider = self.provider_filter.currentData()
        if role != "ALL":
            employees = [item for item in employees if role in item.roles]
        if provider != "ALL":
            employees = [item for item in employees if item.provider_id == provider]
        if self.warning_filter.isChecked():
            employees = [item for item in employees if item.warnings]
        self.employees = employees
        self.table.setRowCount(len(employees))
        for row, employee in enumerate(employees):
            readiness = self.provider_provisioning_service.readiness_for_employee(employee.agent_id)
            values = [
                employee.display_name,
                employee.agent_id,
                status_label(self.language, employee.lifecycle_state),
                ", ".join(role_label(self.language, role) for role in employee.roles),
                PROVIDER_LABELS.get(employee.provider_id, employee.provider_id),
                employee.persona_id or tr(self.language, "not_set"),
                f"{len(employee.effective_permissions)} РїСЂР°РІ",
                readiness_label(self.language, readiness),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, employee.agent_id)
                self.table.setItem(row, column, item)
        if employees:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText(tr(self.language, "no"))

    def selected_agent_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            return None
        return str(items[0].data(Qt.UserRole))

    def _show_selected_detail(self) -> None:
        agent_id = self.selected_agent_id()
        if not agent_id:
            return
        employee = self.service.get_employee(agent_id)
        if employee is None:
            self.detail.setPlainText("РџСЂРѕС„РёР»СЊ РЅРµ РЅР°Р№РґРµРЅ.")
            return
        readiness = self.provider_provisioning_service.readiness_for_employee(employee.agent_id)
        self.detail.setPlainText(format_employee_detail(employee, self.service, readiness, self.language))

    def add_employee(self) -> None:
        dialog = AddEmployeeWizard(
            self.service,
            self.provider_health_service,
            self.provider_provisioning_service,
            self.language,
            self.avatar_dir,
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.console.refresh_all()

    def edit_employee(self) -> None:
        agent_id = self.selected_agent_id()
        if not agent_id:
            return
        dialog = EditEmployeeDialog(self.service, agent_id, self.language, self.avatar_dir, self)
        if dialog.exec() == QDialog.Accepted:
            self.console.refresh_all()

    def lifecycle_action(self, target_state: str) -> None:
        agent_id = self.selected_agent_id()
        if not agent_id:
            return
        reason, ok = QInputDialog.getText(self, "РџСЂРёС‡РёРЅР°", tr(self.language, "reason"))
        if not ok or not reason.strip():
            return
        try:
            if target_state == "SUSPENDED":
                self.service.suspend_agent(agent_id, OWNER_ROLE, reason.strip())
            elif target_state == "ACTIVE":
                employee = self.service.get_employee(agent_id)
                if employee and employee.lifecycle_state == "DRAFT":
                    self.service.activate_agent(agent_id, OWNER_ROLE, reason.strip())
                else:
                    self.service.reactivate_agent(agent_id, OWNER_ROLE, reason.strip())
            elif target_state == "ARCHIVED":
                reply = QMessageBox.question(self, "РђСЂС…РёРІРёСЂРѕРІР°С‚СЊ", "РСЃС‚РѕСЂРёСЏ СЃРѕС…СЂР°РЅРёС‚СЃСЏ. РђСЂС…РёРІРёСЂРѕРІР°С‚СЊ СЃРѕС‚СЂСѓРґРЅРёРєР°?")
                if reply != QMessageBox.Yes:
                    return
                self.service.archive_agent(agent_id, OWNER_ROLE, reason.strip())
        except Exception as exc:
            QMessageBox.warning(self, tr(self.language, "rejected"), friendly_error(str(exc), self.language))
            return
        self.console.refresh_all()


class SkillProgressTab(QWidget):
    def __init__(
        self,
        service: SkillProgressService | None,
        package_service: SkillPackageService | None,
        management_service: ManagementService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.package_service = package_service
        self.management_service = management_service
        self.package_table = QTableWidget(0, 6)
        self.package_table.setHorizontalHeaderLabels(["РќР°РІС‹Рє", "РЎС‚Р°С‚СѓСЃ", "Р’РµСЂСЃРёСЏ", "РќР°Р·РЅР°С‡РµРЅРѕ", "РќР°Р·РЅР°С‡РµРЅРёРµ", "РћР±РЅРѕРІР»РµРЅ"])
        self.package_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.package_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.package_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.package_table.itemSelectionChanged.connect(self._show_selected_package_detail)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "РЎРѕС‚СЂСѓРґРЅРёРє",
                "РќР°РІС‹Рє",
                "РЈСЂРѕРІРµРЅСЊ",
                "РџРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ",
                "Р—Р°РґР°С‡",
                "Р РµРІСЊСЋ",
                "РљРІР°Р»РёС„РёРєР°С†РёСЏ",
                "РџРѕСЃР»РµРґРЅРёР№ СЂРµР·СѓР»СЊС‚Р°С‚",
                "РЎР»РµРґСѓСЋС‰РёР№ С€Р°Рі",
                "Р”РѕСЃС‚РѕРІРµСЂРЅРѕСЃС‚СЊ",
                "РЁРєР°Р»Р°",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)
        create_button = QPushButton("РЎРѕР·РґР°С‚СЊ РїР°РєРµС‚ РЅР°РІС‹РєР°")
        create_button.clicked.connect(self._create_package)
        activate_button = QPushButton("РђРєС‚РёРІРёСЂРѕРІР°С‚СЊ")
        activate_button.clicked.connect(lambda: self._set_selected_package_status("ACTIVE"))
        suspend_button = QPushButton("РџСЂРёРѕСЃС‚Р°РЅРѕРІРёС‚СЊ")
        suspend_button.clicked.connect(lambda: self._set_selected_package_status("SUSPENDED"))
        assign_button = QPushButton("РќР°Р·РЅР°С‡РёС‚СЊ СЃРѕС‚СЂСѓРґРЅРёРєСѓ")
        assign_button.clicked.connect(self._assign_selected_package)
        evidence_button = QPushButton("РџРѕРєР°Р·Р°С‚СЊ РґРѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІР°")
        evidence_button.clicked.connect(self._show_selected_detail)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("РџР°РєРµС‚ РЅР°РІС‹РєР° СѓРїСЂР°РІР»СЏРµС‚СЃСЏ РІР»Р°РґРµР»СЊС†РµРј. РќР°Р·РЅР°С‡РµРЅРёРµ СЃРѕС‚СЂСѓРґРЅРёРєСѓ РЅРµ РїРѕРІС‹С€Р°РµС‚ СѓСЂРѕРІРµРЅСЊ: РїСЂРѕРіСЂРµСЃСЃ СЂР°СЃС‚РµС‚ С‚РѕР»СЊРєРѕ РѕС‚ Р·Р°РґР°С‡, Р°СЂС‚РµС„Р°РєС‚РѕРІ Рё СЂРµРІСЊСЋ."))
        layout.addWidget(self.package_table, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(refresh)
        buttons.addWidget(create_button)
        buttons.addWidget(activate_button)
        buttons.addWidget(suspend_button)
        buttons.addWidget(assign_button)
        buttons.addWidget(evidence_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Evidence-РїСЂРѕРіСЂРµСЃСЃ СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ"))
        layout.addWidget(self.table, 2)
        layout.addWidget(QLabel("Р”РѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІР° Рё РѕСЃРЅРѕРІР°РЅРёРµ СЂР°СЃС‡РµС‚Р°"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        self._refresh_packages()
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Р Р°СЃС‡РµС‚ РЅР°РІС‹РєРѕРІ РЅРµРґРѕСЃС‚СѓРїРµРЅ.")
            return
        rows = self.service.list_progress()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.employee_name,
                row.skill_title,
                row.status,
                row.evidence_summary,
                str(row.tasks_completed),
                str(row.reviews_passed),
                row.qualification,
                row.last_demonstrated or "РЅРµС‚",
                row.next_required_step,
                row.confidence,
                "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.UserRole,
                    "\n".join(
                        [
                            f"РЎРѕС‚СЂСѓРґРЅРёРє: {row.employee_name} ({row.agent_id})",
                            f"РќР°РІС‹Рє: {row.skill_title}",
                            f"РЈСЂРѕРІРµРЅСЊ: {row.status}",
                            f"РџРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ: {row.evidence_summary}",
                            f"РЎР»РµРґСѓСЋС‰РёР№ С€Р°Рі: {row.next_required_step}",
                            f"Р”РѕСЃС‚РѕРІРµСЂРЅРѕСЃС‚СЊ: {row.confidence}",
                            f"РџСЂРѕС†РµРЅС‚: {row.percent}%",
                            f"РћР±РЅРѕРІР»РµРЅ: {row.updated_at or 'РЅРµС‚'}",
                            "",
                            row.basis,
                        ]
                    ),
                )
                self.table.setItem(row_index, column, item)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(row.percent)
            progress.setFormat(f"{row.percent}%")
            self.table.setCellWidget(row_index, 10, progress)
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("РќР°РІС‹РєРѕРІ РїРѕРєР° РЅРµС‚.")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.detail.setPlainText(str(items[0].data(Qt.UserRole) or "РќРµС‚ РґР°РЅРЅС‹С…."))

    def _refresh_packages(self) -> None:
        if self.package_service is None:
            self.package_table.setRowCount(0)
            return
        packages = self.package_service.list_packages()
        assignments = self.package_service.list_assignments()
        by_skill: dict[str, list[str]] = {}
        for assignment in assignments:
            by_skill.setdefault(assignment.skill_id, []).append(f"{assignment.agent_id}: {assignment.state}")
        self.package_table.setRowCount(len(packages))
        for row_index, package in enumerate(packages):
            assigned = by_skill.get(package.skill_id, [])
            values = [
                package.name,
                package.status,
                package.version,
                str(len(assigned)),
                "; ".join(assigned) or "РЅРµС‚",
                package.updated_at or "РЅРµС‚",
            ]
            detail = "\n".join(
                [
                    f"ID: {package.skill_id}",
                    f"РќР°Р·РІР°РЅРёРµ: {package.name}",
                    f"РЎС‚Р°С‚СѓСЃ: {package.status}",
                    f"Р’РµСЂСЃРёСЏ: {package.version}",
                    f"РќР°Р·РЅР°С‡РµРЅРёСЏ: {'; '.join(assigned) or 'РЅРµС‚'}",
                    f"РќР°Р·РЅР°С‡Р°РµРјС‹Рµ СЂРѕР»Рё: {', '.join(package.supported_roles) or 'РЅРµ СѓРєР°Р·Р°РЅС‹'}",
                    f"Р¦РµР»СЊ: {package.purpose or 'РЅРµ СѓРєР°Р·Р°РЅР°'}",
                    f"Р’С…РѕРґС‹: {package.expected_inputs or 'РЅРµ СѓРєР°Р·Р°РЅС‹'}",
                    f"Р’С‹С…РѕРґС‹: {package.expected_outputs or 'РЅРµ СѓРєР°Р·Р°РЅС‹'}",
                    f"Р—Р°РїСЂРµС‰РµРЅРѕ: {package.prohibited_actions or 'РЅРµ СѓРєР°Р·Р°РЅРѕ'}",
                    "Р§РµРє-Р»РёСЃС‚:",
                    *[f"- {item}" for item in package.validation_checklist],
                    "РљРІР°Р»РёС„РёРєР°С†РёРѕРЅРЅС‹Рµ Р·Р°РґР°С‡Рё:",
                    *[f"- {item}" for item in package.qualification_tasks],
                    "",
                    "РРЅСЃС‚СЂСѓРєС†РёРё:",
                    package.instructions or "РЅРµ СѓРєР°Р·Р°РЅС‹",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, package.skill_id)
                item.setData(Qt.UserRole + 1, detail)
                self.package_table.setItem(row_index, column, item)

    def _show_selected_package_detail(self) -> None:
        items = self.package_table.selectedItems()
        if not items:
            return
        self.detail.setPlainText(str(items[0].data(Qt.UserRole + 1) or "РќРµС‚ РґР°РЅРЅС‹С…."))

    def _selected_skill_id(self) -> str | None:
        items = self.package_table.selectedItems()
        if not items:
            QMessageBox.information(self, "РќР°РІС‹Рє", "Р’С‹Р±РµСЂРёС‚Рµ РїР°РєРµС‚ РЅР°РІС‹РєР°.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _create_package(self) -> None:
        if self.package_service is None:
            QMessageBox.warning(self, "РќР°РІС‹РєРё", "РЈРїСЂР°РІР»РµРЅРёРµ РїР°РєРµС‚Р°РјРё РЅР°РІС‹РєРѕРІ РЅРµРґРѕСЃС‚СѓРїРЅРѕ.")
            return
        dialog = SkillPackageDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.package_service.create_package(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "РќР°РІС‹Рє РЅРµ СЃРѕР·РґР°РЅ", str(exc))
            return
        self.refresh()

    def _set_selected_package_status(self, status: str) -> None:
        if self.package_service is None:
            return
        skill_id = self._selected_skill_id()
        if not skill_id:
            return
        try:
            self.package_service.update_status(skill_id, status, actor=OWNER_ROLE, reason="РёР·РјРµРЅРµРЅРѕ С‡РµСЂРµР· Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "РЎС‚Р°С‚СѓСЃ РЅРµ РёР·РјРµРЅРµРЅ", str(exc))
            return
        self.refresh()

    def _assign_selected_package(self) -> None:
        if self.package_service is None:
            return
        skill_id = self._selected_skill_id()
        if not skill_id:
            return
        employees = self.management_service.list_employees()
        if not employees:
            QMessageBox.information(self, "РќР°Р·РЅР°С‡РµРЅРёРµ", "РќРµС‚ СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ РґР»СЏ РЅР°Р·РЅР°С‡РµРЅРёСЏ.")
            return
        dialog = SkillAssignmentDialog(employees, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.package_service.assign_to_employee(
                dialog.agent_id(),
                skill_id,
                state=dialog.state(),
                actor=OWNER_ROLE,
                reason="РЅР°Р·РЅР°С‡РµРЅРѕ С‡РµСЂРµР· Director Console",
            )
        except Exception as exc:
            QMessageBox.warning(self, "РќР°РІС‹Рє РЅРµ РЅР°Р·РЅР°С‡РµРЅ", str(exc))
            return
        self.refresh()


class SkillPackageDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("РЎРѕР·РґР°С‚СЊ РїР°РєРµС‚ РЅР°РІС‹РєР°")
        self.name = QLineEdit()
        self.purpose = QTextEdit()
        self.purpose.setFixedHeight(54)
        self.roles = QLineEdit()
        self.instructions = QTextEdit()
        self.instructions.setFixedHeight(90)
        self.expected_inputs = QLineEdit()
        self.expected_outputs = QLineEdit()
        self.prohibited_actions = QLineEdit()
        self.validation = QTextEdit()
        self.validation.setFixedHeight(72)
        self.qualification = QTextEdit()
        self.qualification.setFixedHeight(72)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("РќР°Р·РІР°РЅРёРµ", self.name)
        layout.addRow("Р¦РµР»СЊ", self.purpose)
        layout.addRow("Р РѕР»Рё С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ", self.roles)
        layout.addRow("РРЅСЃС‚СЂСѓРєС†РёРё", self.instructions)
        layout.addRow("РћР¶РёРґР°РµРјС‹Рµ РІС…РѕРґС‹", self.expected_inputs)
        layout.addRow("РћР¶РёРґР°РµРјС‹Рµ РІС‹С…РѕРґС‹", self.expected_outputs)
        layout.addRow("Р—Р°РїСЂРµС‰РµРЅРЅС‹Рµ РґРµР№СЃС‚РІРёСЏ", self.prohibited_actions)
        layout.addRow("Р§РµРє-Р»РёСЃС‚, РїРѕ СЃС‚СЂРѕРєРµ", self.validation)
        layout.addRow("РљРІР°Р»РёС„РёРєР°С†РёРѕРЅРЅС‹Рµ Р·Р°РґР°С‡Рё", self.qualification)
        layout.addRow(buttons)

    def values(self) -> dict[str, object]:
        return {
            "name": self.name.text(),
            "purpose": self.purpose.toPlainText(),
            "supported_roles": _lines_or_commas(self.roles.text()),
            "instructions": self.instructions.toPlainText(),
            "expected_inputs": self.expected_inputs.text(),
            "expected_outputs": self.expected_outputs.text(),
            "prohibited_actions": self.prohibited_actions.text(),
            "validation_checklist": _lines(self.validation.toPlainText()),
            "qualification_tasks": _lines(self.qualification.toPlainText()),
            "status": "DRAFT",
        }


class SkillAssignmentDialog(QDialog):
    def __init__(self, employees: list[EmployeeSummary], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("РќР°Р·РЅР°С‡РёС‚СЊ РЅР°РІС‹Рє")
        self.employee = QComboBox()
        for item in employees:
            self.employee.addItem(f"{item.display_name} ({item.agent_id})", item.agent_id)
        self.skill_state = QComboBox()
        for state in ("ASSIGNED", "STUDYING", "PRACTICED", "DEMONSTRATED", "REVIEWED", "REQUIRES_RETRAINING"):
            self.skill_state.addItem(state, state)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("РЎРѕС‚СЂСѓРґРЅРёРє", self.employee)
        layout.addRow("РЎРѕСЃС‚РѕСЏРЅРёРµ", self.skill_state)
        layout.addRow(buttons)

    def agent_id(self) -> str:
        return str(self.employee.currentData())

    def state(self) -> str:
        return str(self.skill_state.currentData())


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _lines_or_commas(text: str) -> list[str]:
    return [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]


class KnowledgeTab(QWidget):
    def __init__(self, service: KnowledgeService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Статус", "Надежность", "Источник", "Роли", "Теги", "Версия", "Обновлено", "Подано", "Применено", "Игнор.", "Ошибка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Р”РѕР±Р°РІРёС‚СЊ РєР°СЂС‚РѕС‡РєСѓ")
        create.clicked.connect(self._create_card)
        activate = QPushButton("РђРєС‚РёРІРёСЂРѕРІР°С‚СЊ")
        activate.clicked.connect(lambda: self._set_selected_status("ACTIVE"))
        review = QPushButton("РќР° СЂРµРІСЊСЋ")
        review.clicked.connect(lambda: self._set_selected_status("NEEDS_REVIEW"))
        reject = QPushButton("РћС‚РєР»РѕРЅРёС‚СЊ")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Карточки знаний управляются владельцем. ACTIVE попадают в контекст, а применение считается отдельно: SUPPLIED / APPLIED / IGNORED / MISAPPLIED."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, activate, review, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("РљР°СЂС‚РѕС‡РєР° Рё Р°СѓРґРёС‚"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("РЎРµСЂРІРёСЃ Р·РЅР°РЅРёР№ РЅРµРґРѕСЃС‚СѓРїРµРЅ.")
            return
        cards = self.service.list_cards()
        usage_counts = self.service.usage_counts_by_card()
        self.table.setRowCount(len(cards))
        for row_index, card in enumerate(cards):
            counts = usage_counts.get(card.knowledge_id)
            values = [
                card.title,
                card.status,
                card.source_authority,
                card.source_title or card.source_uri or "РЅРµ СѓРєР°Р·Р°РЅ",
                ", ".join(card.role_ids) or "РІСЃРµ",
                ", ".join(card.tags) or "РЅРµС‚",
                card.version,
                card.updated_at or "РЅРµС‚",
                str(counts.supplied if counts else 0),
                str(counts.applied if counts else 0),
                str(counts.ignored if counts else 0),
                str(counts.misapplied if counts else 0),
            ]
            detail = "\n".join(
                [
                    f"ID: {card.knowledge_id}",
                    f"РќР°Р·РІР°РЅРёРµ: {card.title}",
                    f"РЎС‚Р°С‚СѓСЃ: {card.status}",
                    f"РќР°РґРµР¶РЅРѕСЃС‚СЊ РёСЃС‚РѕС‡РЅРёРєР°: {card.source_authority}",
                    f"РўРёРї РёСЃС‚РѕС‡РЅРёРєР°: {card.source_type}",
                    f"РСЃС‚РѕС‡РЅРёРє: {card.source_title or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"РЎСЃС‹Р»РєР°/РїСѓС‚СЊ: {card.source_uri or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"РҐСЌС€: {card.source_hash or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"Р РѕР»Рё: {', '.join(card.role_ids) or 'РІСЃРµ'}",
                    f"РўРµРіРё: {', '.join(card.tags) or 'РЅРµС‚'}",
                    f"Р’РµСЂСЃРёСЏ: {card.version}",
                    f"Р—Р°РјРµС‚РєРё СЂРµРІСЊСЋ: {card.review_notes or 'РЅРµС‚'}",
                    f"Использование: SUPPLIED={counts.supplied if counts else 0}; APPLIED={counts.applied if counts else 0}; IGNORED={counts.ignored if counts else 0}; MISAPPLIED={counts.misapplied if counts else 0}",
                    "",
                    "РљСЂР°С‚РєРѕ:",
                    card.summary or "РЅРµ Р·Р°РїРѕР»РЅРµРЅРѕ",
                    "",
                    "РЎРѕРґРµСЂР¶Р°РЅРёРµ:",
                    card.content or "РЅРµ Р·Р°РїРѕР»РЅРµРЅРѕ",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, card.knowledge_id)
                item.setData(Qt.UserRole + 1, detail)
                self.table.setItem(row_index, column, item)
        if cards:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("РљР°СЂС‚РѕС‡РµРє Р·РЅР°РЅРёР№ РїРѕРєР° РЅРµС‚.")

    def _selected_knowledge_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Р—РЅР°РЅРёСЏ", "Р’С‹Р±РµСЂРёС‚Рµ РєР°СЂС‚РѕС‡РєСѓ.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "РќРµС‚ РґР°РЅРЅС‹С….")
        knowledge_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and knowledge_id:
            events = self.service.list_events(knowledge_id)
            if events:
                detail += "\n\nРђСѓРґРёС‚:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
        self.detail.setPlainText(detail)

    def _create_card(self) -> None:
        if self.service is None:
            return
        dialog = KnowledgeCardDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_card(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "Р—РЅР°РЅРёРµ РЅРµ СЃРѕР·РґР°РЅРѕ", str(exc))
            return
        self.refresh()

    def _set_selected_status(self, status: str) -> None:
        if self.service is None:
            return
        knowledge_id = self._selected_knowledge_id()
        if not knowledge_id:
            return
        try:
            self.service.update_status(knowledge_id, status, actor=OWNER_ROLE, reason="РёР·РјРµРЅРµРЅРѕ С‡РµСЂРµР· Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "РЎС‚Р°С‚СѓСЃ РЅРµ РёР·РјРµРЅРµРЅ", str(exc))
            return
        self.refresh()


class KnowledgeCardDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Р”РѕР±Р°РІРёС‚СЊ РєР°СЂС‚РѕС‡РєСѓ Р·РЅР°РЅРёР№")
        self.title = QLineEdit()
        self.summary = QTextEdit()
        self.summary.setFixedHeight(64)
        self.content = QTextEdit()
        self.content.setFixedHeight(120)
        self.source_type = QLineEdit("internal_note")
        self.source_title = QLineEdit()
        self.source_uri = QLineEdit()
        self.source_authority = QComboBox()
        for item in SOURCE_AUTHORITIES:
            self.source_authority.addItem(item, item)
        self.roles = QLineEdit()
        self.tags = QLineEdit()
        self.review_notes = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("РќР°Р·РІР°РЅРёРµ", self.title)
        layout.addRow("РљСЂР°С‚РєРѕ", self.summary)
        layout.addRow("РЎРѕРґРµСЂР¶Р°РЅРёРµ", self.content)
        layout.addRow("РўРёРї РёСЃС‚РѕС‡РЅРёРєР°", self.source_type)
        layout.addRow("РќР°Р·РІР°РЅРёРµ РёСЃС‚РѕС‡РЅРёРєР°", self.source_title)
        layout.addRow("РЎСЃС‹Р»РєР°/РїСѓС‚СЊ", self.source_uri)
        layout.addRow("РќР°РґРµР¶РЅРѕСЃС‚СЊ РёСЃС‚РѕС‡РЅРёРєР°", self.source_authority)
        layout.addRow("Р РѕР»Рё С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ", self.roles)
        layout.addRow("РўРµРіРё С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ", self.tags)
        layout.addRow("Р—Р°РјРµС‚РєРё СЂРµРІСЊСЋ", self.review_notes)
        layout.addRow(buttons)

    def values(self) -> dict[str, object]:
        return {
            "title": self.title.text(),
            "summary": self.summary.toPlainText(),
            "content": self.content.toPlainText(),
            "source_type": self.source_type.text(),
            "source_title": self.source_title.text(),
            "source_uri": self.source_uri.text(),
            "source_authority": str(self.source_authority.currentData()),
            "role_ids": _lines_or_commas(self.roles.text()),
            "tags": _lines_or_commas(self.tags.text()),
            "review_notes": self.review_notes.text(),
            "status": "DRAFT",
        }


class StandardsTab(QWidget):
    def __init__(self, service: StandardsService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(
            ["Код", "Название", "Статус", "Обязательность", "Источник", "Роли", "Теги", "Версия", "Обновлено", "Подано", "Применено", "Игнор.", "Ошибка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Р”РѕР±Р°РІРёС‚СЊ СЃС‚Р°РЅРґР°СЂС‚")
        create.clicked.connect(self._create_card)
        activate = QPushButton("РђРєС‚РёРІРёСЂРѕРІР°С‚СЊ")
        activate.clicked.connect(lambda: self._set_selected_status("ACTIVE"))
        suspend = QPushButton("РџСЂРёРѕСЃС‚Р°РЅРѕРІРёС‚СЊ")
        suspend.clicked.connect(lambda: self._set_selected_status("SUSPENDED"))
        reject = QPushButton("РћС‚РєР»РѕРЅРёС‚СЊ")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Стандарты управляются владельцем. ACTIVE попадают в контекст, а применение считается отдельно: SUPPLIED / APPLIED / IGNORED / MISAPPLIED."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, activate, suspend, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("РўСЂРµР±РѕРІР°РЅРёРµ Рё Р°СѓРґРёС‚"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("РЎРµСЂРІРёСЃ СЃС‚Р°РЅРґР°СЂС‚РѕРІ РЅРµРґРѕСЃС‚СѓРїРµРЅ.")
            return
        cards = self.service.list_cards()
        usage_counts = self.service.usage_counts_by_card()
        self.table.setRowCount(len(cards))
        for row_index, card in enumerate(cards):
            counts = usage_counts.get(card.standard_id)
            values = [
                card.code,
                card.title,
                card.status,
                card.mandatory_level,
                card.source_title or card.source_uri or "РЅРµ СѓРєР°Р·Р°РЅ",
                ", ".join(card.role_ids) or "РІСЃРµ",
                ", ".join(card.tags) or "РЅРµС‚",
                card.version,
                card.updated_at or "РЅРµС‚",
                str(counts.supplied if counts else 0),
                str(counts.applied if counts else 0),
                str(counts.ignored if counts else 0),
                str(counts.misapplied if counts else 0),
            ]
            detail = "\n".join(
                [
                    f"ID: {card.standard_id}",
                    f"РљРѕРґ: {card.code}",
                    f"РќР°Р·РІР°РЅРёРµ: {card.title}",
                    f"РЎС‚Р°С‚СѓСЃ: {card.status}",
                    f"РћР±СЏР·Р°С‚РµР»СЊРЅРѕСЃС‚СЊ: {card.mandatory_level}",
                    f"Authority: {card.authority}",
                    f"РСЃС‚РѕС‡РЅРёРє: {card.source_title or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"РЎСЃС‹Р»РєР°/РїСѓС‚СЊ: {card.source_uri or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"РҐСЌС€: {card.source_hash or 'РЅРµ СѓРєР°Р·Р°РЅ'}",
                    f"Р РѕР»Рё: {', '.join(card.role_ids) or 'РІСЃРµ'}",
                    f"РўРµРіРё: {', '.join(card.tags) or 'РЅРµС‚'}",
                    f"Р’РµСЂСЃРёСЏ: {card.version}",
                    f"РћР±Р»Р°СЃС‚СЊ РїСЂРёРјРµРЅРµРЅРёСЏ: {card.scope or 'РЅРµ СѓРєР°Р·Р°РЅР°'}",
                    f"Р—Р°РјРµС‚РєРё СЂРµРІСЊСЋ: {card.review_notes or 'РЅРµС‚'}",
                    f"Использование: SUPPLIED={counts.supplied if counts else 0}; APPLIED={counts.applied if counts else 0}; IGNORED={counts.ignored if counts else 0}; MISAPPLIED={counts.misapplied if counts else 0}",
                    "",
                    "РўСЂРµР±РѕРІР°РЅРёРµ:",
                    card.requirement or "РЅРµ Р·Р°РїРѕР»РЅРµРЅРѕ",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, card.standard_id)
                item.setData(Qt.UserRole + 1, detail)
                self.table.setItem(row_index, column, item)
        if cards:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("РЎС‚Р°РЅРґР°СЂС‚РѕРІ РїРѕРєР° РЅРµС‚.")

    def _selected_standard_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "РЎС‚Р°РЅРґР°СЂС‚С‹", "Р’С‹Р±РµСЂРёС‚Рµ СЃС‚Р°РЅРґР°СЂС‚.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "РќРµС‚ РґР°РЅРЅС‹С….")
        standard_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and standard_id:
            events = self.service.list_events(standard_id)
            if events:
                detail += "\n\nРђСѓРґРёС‚:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
        self.detail.setPlainText(detail)

    def _create_card(self) -> None:
        if self.service is None:
            return
        dialog = StandardCardDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_card(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "РЎС‚Р°РЅРґР°СЂС‚ РЅРµ СЃРѕР·РґР°РЅ", str(exc))
            return
        self.refresh()

    def _set_selected_status(self, status: str) -> None:
        if self.service is None:
            return
        standard_id = self._selected_standard_id()
        if not standard_id:
            return
        try:
            self.service.update_status(standard_id, status, actor=OWNER_ROLE, reason="РёР·РјРµРЅРµРЅРѕ С‡РµСЂРµР· Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "РЎС‚Р°С‚СѓСЃ РЅРµ РёР·РјРµРЅРµРЅ", str(exc))
            return
        self.refresh()


class StandardCardDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Р”РѕР±Р°РІРёС‚СЊ СЃС‚Р°РЅРґР°СЂС‚")
        self.code = QLineEdit()
        self.title = QLineEdit()
        self.requirement = QTextEdit()
        self.requirement.setFixedHeight(110)
        self.scope = QLineEdit()
        self.source_title = QLineEdit()
        self.source_uri = QLineEdit()
        self.authority = QComboBox()
        for item in STANDARD_AUTHORITIES:
            self.authority.addItem(item, item)
        self.mandatory = QComboBox()
        for item in MANDATORY_LEVELS:
            self.mandatory.addItem(item, item)
        self.roles = QLineEdit()
        self.tags = QLineEdit()
        self.review_notes = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("РљРѕРґ", self.code)
        layout.addRow("РќР°Р·РІР°РЅРёРµ", self.title)
        layout.addRow("РўСЂРµР±РѕРІР°РЅРёРµ", self.requirement)
        layout.addRow("РћР±Р»Р°СЃС‚СЊ РїСЂРёРјРµРЅРµРЅРёСЏ", self.scope)
        layout.addRow("РСЃС‚РѕС‡РЅРёРє", self.source_title)
        layout.addRow("РЎСЃС‹Р»РєР°/РїСѓС‚СЊ", self.source_uri)
        layout.addRow("Authority", self.authority)
        layout.addRow("РћР±СЏР·Р°С‚РµР»СЊРЅРѕСЃС‚СЊ", self.mandatory)
        layout.addRow("Р РѕР»Рё С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ", self.roles)
        layout.addRow("РўРµРіРё С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ", self.tags)
        layout.addRow("Р—Р°РјРµС‚РєРё СЂРµРІСЊСЋ", self.review_notes)
        layout.addRow(buttons)

    def values(self) -> dict[str, object]:
        return {
            "code": self.code.text(),
            "title": self.title.text(),
            "requirement": self.requirement.toPlainText(),
            "scope": self.scope.text(),
            "source_title": self.source_title.text(),
            "source_uri": self.source_uri.text(),
            "authority": str(self.authority.currentData()),
            "mandatory_level": str(self.mandatory.currentData()),
            "role_ids": _lines_or_commas(self.roles.text()),
            "tags": _lines_or_commas(self.tags.text()),
            "review_notes": self.review_notes.text(),
            "status": "DRAFT",
        }


class ArtifactsTab(QWidget):
    def __init__(self, service: ArtifactService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["РџСѓС‚СЊ", "РЎС‚Р°С‚СѓСЃ", "РџСЂРѕРІРµСЂРєР°", "QA", "Р—Р°РґР°С‡Р°", "Р РѕР»СЊ", "Run", "РўРёРї", "Р Р°Р·РјРµСЂ", "РР·РјРµРЅРµРЅ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)
        open_file = QPushButton("РћС‚РєСЂС‹С‚СЊ С„Р°Р№Р»")
        open_file.clicked.connect(self._open_selected_file)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("РђСЂС‚РµС„Р°РєС‚С‹ РїРѕРєР°Р·С‹РІР°СЋС‚ СЂРµР°Р»СЊРЅС‹Рµ СЃР»РµРґС‹ СЂР°Р±РѕС‚С‹: РЅР°Р№РґРµРЅРЅС‹Рµ С„Р°Р№Р»С‹, РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‰РёРµ Р·Р°СЏРІР»РµРЅРёСЏ Рё С…СЌС€Рё РїРѕРґС‚РІРµСЂР¶РґРµРЅРЅС‹С… С„Р°Р№Р»РѕРІ."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        buttons.addWidget(refresh)
        buttons.addWidget(open_file)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Р”РµС‚Р°Р»Рё Р°СЂС‚РµС„Р°РєС‚Р°"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("РЎРµСЂРІРёСЃ Р°СЂС‚РµС„Р°РєС‚РѕРІ РЅРµРґРѕСЃС‚СѓРїРµРЅ.")
            return
        artifacts = self.service.list_artifacts()
        self.table.setRowCount(len(artifacts))
        for row_index, artifact in enumerate(artifacts):
            related_findings = self.service.related_findings(artifact)
            related_links = self.service.list_finding_links(artifact_id=artifact.artifact_id)
            links_by_finding = {link.finding_id: link for link in related_links}
            values = [
                artifact.relative_path,
                artifact.status,
                artifact.validation_status,
                str(len(related_findings)),
                artifact.task_id or "РЅРµС‚",
                artifact.authoring_role or "РЅРµС‚",
                artifact.created_by_run_id or "РЅРµС‚",
                artifact.artifact_type or "file",
                str(artifact.size) if artifact.size is not None else "РЅРµС‚",
                artifact.last_modified_time or "РЅРµС‚",
            ]
            detail = "\n".join(
                [
                    f"ID: {artifact.artifact_id}",
                    f"РџСѓС‚СЊ: {artifact.relative_path}",
                    f"Р—Р°РґР°С‡Р°: {artifact.task_id or 'РЅРµС‚'}",
                    f"РџСЂРѕРµРєС‚: {artifact.project_id or 'РЅРµС‚'}",
                    f"РЎС‚Р°С‚СѓСЃ: {artifact.status}",
                    f"РџСЂРѕРІРµСЂРєР°: {artifact.validation_status}",
                    f"Р РѕР»СЊ Р°РІС‚РѕСЂР°: {artifact.authoring_role or 'РЅРµС‚'}",
                    f"Run: {artifact.created_by_run_id or 'РЅРµС‚'}",
                    f"РўРёРї: {artifact.artifact_type or 'file'}",
                    f"Media type: {artifact.media_type or 'РЅРµС‚'}",
                    f"Р Р°Р·РјРµСЂ: {artifact.size if artifact.size is not None else 'РЅРµС‚'}",
                    f"SHA-256: {artifact.sha256 or 'РЅРµС‚'}",
                    f"Revision: {artifact.current_revision or 'РЅРµС‚'}",
                    f"РЈРґР°Р»РµРЅ: {'РґР°' if artifact.deleted else 'РЅРµС‚'}",
                    f"РР·РјРµРЅРµРЅ: {artifact.last_modified_time or 'РЅРµС‚'}",
                    "",
                    "QA findings:",
                    *(
                        [
                            (
                                f"- {finding.severity} / {finding.status}: {finding.description}"
                                + (
                                    f" | link: {links_by_finding[finding.finding_id].match_type}/{links_by_finding[finding.finding_id].confidence}"
                                    if finding.finding_id in links_by_finding
                                    else ""
                                )
                                + (f" | Р Т‘Р ВµР в„–РЎРѓРЎвЂљР Р†Р С‘Р Вµ: {finding.required_action}" if finding.required_action else "")
                            )
                            for finding in related_findings
                        ]
                        or ["Р Р…Р ВµРЎвЂљ"]
                    ),
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, artifact.artifact_id)
                item.setData(Qt.UserRole + 1, detail)
                item.setData(Qt.UserRole + 2, artifact.relative_path)
                self.table.setItem(row_index, column, item)
        if artifacts:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("Р С’РЎР‚РЎвЂљР ВµРЎвЂћР В°Р С”РЎвЂљР С•Р Р† Р С—Р С•Р С”Р В° Р Р…Р ВµРЎвЂљ.")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.detail.setPlainText(str(items[0].data(Qt.UserRole + 1) or "Р СњР ВµРЎвЂљ Р Т‘Р В°Р Р…Р Р…РЎвЂ№РЎвЂ¦."))

    def _open_selected_file(self) -> None:
        if self.service is None:
            return
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Р С’РЎР‚РЎвЂљР ВµРЎвЂћР В°Р С”РЎвЂљРЎвЂ№", "Р вЂ™РЎвЂ№Р В±Р ВµРЎР‚Р С‘РЎвЂљР Вµ Р В°РЎР‚РЎвЂљР ВµРЎвЂћР В°Р С”РЎвЂљ.")
            return
        relative_path = str(items[0].data(Qt.UserRole + 2) or "")
        target = (self.service.workspace_root / relative_path).resolve(strict=False)
        if not target.is_file() or not target.is_relative_to(self.service.workspace_root):
            QMessageBox.information(self, "Р С’РЎР‚РЎвЂљР ВµРЎвЂћР В°Р С”РЎвЂљРЎвЂ№", "Р В¤Р В°Р в„–Р В» Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р… Р Р† РЎР‚Р В°Р В±Р С•РЎвЂЎР ВµР в„– Р С—Р В°Р С—Р С”Р Вµ.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


class FindingsTab(QWidget):
    def __init__(self, service: FindingService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            ["Р—Р°РґР°С‡Р°", "РЎРµСЂСЊРµР·РЅРѕСЃС‚СЊ", "РЎС‚Р°С‚СѓСЃ", "РЈРІРµСЂРµРЅРЅРѕСЃС‚СЊ", "РЎС‚Р°РЅРґР°СЂС‚", "РђСЂС‚РµС„Р°РєС‚", "Р›РѕРєР°С†РёСЏ", "РћРїРёСЃР°РЅРёРµ", "Р”РµР№СЃС‚РІРёРµ", "РћР±РЅРѕРІР»РµРЅРѕ"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Р”РѕР±Р°РІРёС‚СЊ finding")
        create.clicked.connect(self._create_finding)
        rework = QPushButton("Р’ РґРѕСЂР°Р±РѕС‚РєСѓ")
        rework.clicked.connect(lambda: self._set_selected_status("IN_REWORK"))
        recheck = QPushButton("РќР° РїРµСЂРµРїСЂРѕРІРµСЂРєСѓ")
        recheck.clicked.connect(lambda: self._set_selected_status("READY_FOR_RECHECK"))
        resolved = QPushButton("Р—Р°РєСЂС‹С‚СЊ")
        resolved.clicked.connect(lambda: self._set_selected_status("RESOLVED"))
        accepted = QPushButton("РџСЂРёРЅСЏС‚СЊ СЂРёСЃРє")
        accepted.clicked.connect(lambda: self._set_selected_status("ACCEPTED_RISK"))
        reject = QPushButton("РћС‚РєР»РѕРЅРёС‚СЊ")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Findings С„РёРєСЃРёСЂСѓСЋС‚ СЂРµР°Р»СЊРЅС‹Рµ QA-Р·Р°РјРµС‡Р°РЅРёСЏ. HIGH/CRITICAL РѕС‚РєСЂС‹С‚С‹Рµ findings Р±Р»РѕРєРёСЂСѓСЋС‚ Р·Р°РІРµСЂС€РµРЅРёРµ Р·Р°РґР°С‡Рё."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, rework, recheck, resolved, accepted, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Finding Рё Р°СѓРґРёС‚"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("РЎРµСЂРІРёСЃ findings РЅРµРґРѕСЃС‚СѓРїРµРЅ.")
            return
        findings = self.service.list_findings()
        self.table.setRowCount(len(findings))
        for row_index, finding in enumerate(findings):
            values = [
                finding.task_id,
                finding.severity,
                finding.status,
                finding.confidence,
                finding.standard_id or "РЅРµС‚",
                finding.affected_artifact or "РЅРµС‚",
                finding.location or "РЅРµС‚",
                finding.description,
                finding.required_action or "РЅРµ СѓРєР°Р·Р°РЅРѕ",
                finding.updated_at or "РЅРµС‚",
            ]
            detail = "\n".join(
                [
                    f"ID: {finding.finding_id}",
                    f"Р—Р°РґР°С‡Р°: {finding.task_id}",
                    f"РўРёРї: {finding.finding_type or 'QA_FINDING'}",
                    f"РЎРµСЂСЊРµР·РЅРѕСЃС‚СЊ: {finding.severity}",
                    f"РЎС‚Р°С‚СѓСЃ: {finding.status}",
                    f"РЈРІРµСЂРµРЅРЅРѕСЃС‚СЊ: {finding.confidence}",
                    f"РЎС‚Р°РЅРґР°СЂС‚: {finding.standard_id or 'РЅРµС‚'}",
                    f"РђСЂС‚РµС„Р°РєС‚: {finding.affected_artifact or 'РЅРµС‚'}",
                    f"Р›РѕРєР°С†РёСЏ: {finding.location or 'РЅРµС‚'}",
                    f"Repeat key: {finding.repeat_key or 'РЅРµС‚'}",
                    f"РќРµР·Р°РІРёСЃРёРјР°СЏ РїРµСЂРµРїСЂРѕРІРµСЂРєР°: {finding.independent_recheck_status or 'РЅРµС‚'}",
                    "",
                    "РћРїРёСЃР°РЅРёРµ:",
                    finding.description,
                    "",
                    "Р’Р»РёСЏРЅРёРµ:",
                    finding.impact or "РЅРµ СѓРєР°Р·Р°РЅРѕ",
                    "",
                    "РўСЂРµР±СѓРµРјРѕРµ РґРµР№СЃС‚РІРёРµ:",
                    finding.required_action or "РЅРµ СѓРєР°Р·Р°РЅРѕ",
                    "",
                    "Evidence:",
                    finding.evidence or "{}",
                    "",
                    "Р РµС€РµРЅРёРµ:",
                    finding.resolution or "РЅРµС‚",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, finding.finding_id)
                item.setData(Qt.UserRole + 1, detail)
                self.table.setItem(row_index, column, item)
        if findings:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("Findings РїРѕРєР° РЅРµС‚.")

    def _selected_finding_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Findings", "Р’С‹Р±РµСЂРёС‚Рµ finding.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "РќРµС‚ РґР°РЅРЅС‹С….")
        finding_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and finding_id:
            events = self.service.list_events(finding_id)
            if events:
                detail += "\n\nРђСѓРґРёС‚:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
        self.detail.setPlainText(detail)

    def _create_finding(self) -> None:
        if self.service is None:
            return
        tasks = self.service.database.list_tasks()
        if not tasks:
            QMessageBox.information(self, "Findings", "РЎРЅР°С‡Р°Р»Р° РЅСѓР¶РЅР° С…РѕС‚СЏ Р±С‹ РѕРґРЅР° Р·Р°РґР°С‡Р°.")
            return
        dialog = FindingDialog(tasks, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_finding(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "Finding РЅРµ СЃРѕР·РґР°РЅ", str(exc))
            return
        self.refresh()

    def _set_selected_status(self, status: str) -> None:
        if self.service is None:
            return
        finding_id = self._selected_finding_id()
        if not finding_id:
            return
        resolution = ""
        if status in {"RESOLVED", "ACCEPTED_RISK", "REJECTED"}:
            resolution, ok = QInputDialog.getText(self, "Р РµС€РµРЅРёРµ", "РљСЂР°С‚РєРѕ СѓРєР°Р¶РёС‚Рµ РѕСЃРЅРѕРІР°РЅРёРµ:")
            if not ok:
                return
        try:
            self.service.update_status(finding_id, status, actor=OWNER_ROLE, resolution=resolution)
        except Exception as exc:
            QMessageBox.warning(self, "РЎС‚Р°С‚СѓСЃ РЅРµ РёР·РјРµРЅРµРЅ", str(exc))
            return
        self.refresh()


class FindingDialog(QDialog):
    def __init__(self, tasks, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Р”РѕР±Р°РІРёС‚СЊ finding")
        self.task = QComboBox()
        for row in tasks:
            self.task.addItem(f"{row['title']} ({row['id']}; {row['state']})", row["id"])
        self.severity = QComboBox()
        for item in FINDING_SEVERITIES:
            self.severity.addItem(item, item)
        self.severity.setCurrentText("MEDIUM")
        self.confidence = QComboBox()
        for item in FINDING_CONFIDENCE:
            self.confidence.addItem(item, item)
        self.confidence.setCurrentText("MEDIUM")
        self.standard_id = QLineEdit()
        self.artifact = QLineEdit()
        self.location = QLineEdit()
        self.description = QTextEdit()
        self.description.setFixedHeight(86)
        self.impact = QTextEdit()
        self.impact.setFixedHeight(58)
        self.required_action = QTextEdit()
        self.required_action.setFixedHeight(58)
        self.evidence = QTextEdit()
        self.evidence.setFixedHeight(58)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("Р—Р°РґР°С‡Р°", self.task)
        layout.addRow("РЎРµСЂСЊРµР·РЅРѕСЃС‚СЊ", self.severity)
        layout.addRow("РЈРІРµСЂРµРЅРЅРѕСЃС‚СЊ", self.confidence)
        layout.addRow("Standard ID", self.standard_id)
        layout.addRow("РђСЂС‚РµС„Р°РєС‚", self.artifact)
        layout.addRow("Р›РѕРєР°С†РёСЏ", self.location)
        layout.addRow("РћРїРёСЃР°РЅРёРµ", self.description)
        layout.addRow("Р’Р»РёСЏРЅРёРµ", self.impact)
        layout.addRow("РўСЂРµР±СѓРµРјРѕРµ РґРµР№СЃС‚РІРёРµ", self.required_action)
        layout.addRow("Evidence", self.evidence)
        layout.addRow(buttons)

    def values(self) -> dict[str, object]:
        return {
            "task_id": str(self.task.currentData()),
            "severity": str(self.severity.currentData()),
            "confidence": str(self.confidence.currentData()),
            "standard_id": self.standard_id.text().strip() or None,
            "affected_artifact": self.artifact.text(),
            "location": self.location.text(),
            "description": self.description.toPlainText(),
            "impact": self.impact.toPlainText(),
            "required_action": self.required_action.toPlainText(),
            "evidence": self.evidence.toPlainText(),
        }


class RolesTab(QWidget):
    def __init__(self, service: ManagementService, language: str, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "role"),
                tr(language, "description"),
                tr(language, "responsibilities"),
                tr(language, "restrictions"),
                tr(language, "employees"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(language, "roles_readonly")))
        layout.addWidget(self.table)

    def refresh(self) -> None:
        roles = self.service.list_roles()
        employees = self.service.list_employees()
        self.table.setRowCount(len(roles))
        for row, role in enumerate(roles):
            role_id = str(role["role_id"])
            assigned = [employee.display_name for employee in employees if role_id in employee.roles]
            values = [
                role_label(self.language, role_id),
                str(role["description"]),
                ", ".join(json.loads(role["responsibilities"] or "[]")),
                ", ".join(json.loads(role["restrictions"] or "[]")),
                ", ".join(assigned) or tr(self.language, "no"),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))


class PermissionsTab(QWidget):
    def __init__(self, service: ManagementService, language: str, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language
        self.employee_select = QComboBox()
        self.employee_select.currentIndexChanged.connect(self.refresh_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.employee_select)
        layout.addWidget(self.detail)

    def refresh(self) -> None:
        current = self.employee_select.currentData()
        self.employee_select.blockSignals(True)
        self.employee_select.clear()
        for employee in self.service.list_employees():
            self.employee_select.addItem(f"{employee.display_name} ({employee.agent_id})", employee.agent_id)
        if current:
            index = self.employee_select.findData(current)
            if index >= 0:
                self.employee_select.setCurrentIndex(index)
        self.employee_select.blockSignals(False)
        self.refresh_detail()

    def refresh_detail(self) -> None:
        agent_id = self.employee_select.currentData()
        if not agent_id:
            self.detail.setPlainText("")
            return
        employee = self.service.get_employee(str(agent_id))
        if employee is None:
            self.detail.setPlainText(tr(self.language, "unknown_agent"))
            return
        inherited = sorted(self.service.inherited_permissions(employee.roles))
        lines = [
            f"{tr(self.language, 'employee')}: {employee.display_name}",
            f"{tr(self.language, 'agent_id')}: {employee.agent_id}",
            "",
            f"{tr(self.language, 'inherited_permissions')}:",
            *[f"+ {permission_label(self.language, permission)}" for permission in inherited],
            "",
            f"{tr(self.language, 'direct_grants')}:",
            *[f"+ {permission_label(self.language, permission)}" for permission in employee.direct_permissions],
            "",
            f"{tr(self.language, 'direct_denies')}:",
            *[f"- {permission_label(self.language, permission)}" for permission in employee.permission_denies],
            "",
            f"{tr(self.language, 'effective_permissions')}:",
            *[f"= {permission_label(self.language, permission)}" for permission in employee.effective_permissions],
            "",
            f"{tr(self.language, 'warnings')}:",
            *(employee.warnings or [tr(self.language, "no")]),
        ]
        self.detail.setPlainText("\n".join(lines))


class ProvidersTab(QWidget):
    def __init__(
        self,
        registry: ProviderRegistry,
        health_service: ProviderHealthService,
        provisioning_service: ProviderProvisioningService,
        management_service: ManagementService,
        language: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.registry = registry
        self.health_service = health_service
        self.provisioning_service = provisioning_service
        self.management_service = management_service
        self.language = language
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "provider"),
                tr(language, "adapter"),
                tr(language, "install"),
                tr(language, "version"),
                tr(language, "auth"),
                tr(language, "access"),
                tr(language, "health"),
                tr(language, "capabilities"),
                tr(language, "employees"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.table.itemSelectionChanged.connect(self.show_selected)
        refresh = QPushButton(tr(language, "repeat_check"))
        refresh.clicked.connect(self.run_checks)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(language, "provider_page_note")))
        layout.addWidget(self.table, 2)
        layout.addWidget(refresh)
        layout.addWidget(QLabel(tr(language, "diagnostics")))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        profiles = self.registry.profiles()
        self.table.setRowCount(len(profiles))
        employees = self.management_service.list_employees()
        for row, profile in enumerate(profiles):
            health = self.health_service.latest_health(profile.provider_id) or self.health_service.check_provider(profile.provider_id)
            assigned = [employee.display_name for employee in employees if employee.provider_id == profile.provider_id]
            values = [
                profile.display_name,
                profile.adapter_id,
                health.installation_status,
                health.detected_version or tr(self.language, "not_checked"),
                health.authentication_status,
                health.access_status,
                health.health_status,
                health.capability_status,
                ", ".join(assigned) or tr(self.language, "no"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, profile.provider_id)
                self.table.setItem(row, column, item)
        if profiles:
            self.table.selectRow(0)

    def selected_provider_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            return None
        return str(items[0].data(Qt.UserRole))

    def show_selected(self) -> None:
        provider_id = self.selected_provider_id()
        if not provider_id:
            return
        profile = self.registry.get(provider_id)
        health = self.health_service.latest_health(provider_id)
        if profile is None:
            self.detail.setPlainText(tr(self.language, "unknown_provider"))
            return
        lines = [
            f"{tr(self.language, 'provider_id')}: {profile.provider_id}",
            f"{tr(self.language, 'display_name')}: {profile.display_name}",
            f"{tr(self.language, 'family')}: {profile.provider_family}",
            f"{tr(self.language, 'adapter')}: {profile.adapter_id}",
            f"{tr(self.language, 'executables')}: {', '.join(profile.executable_names)}",
            f"{tr(self.language, 'install_strategy')}: {profile.installation_strategy}",
            f"{tr(self.language, 'auth_strategy')}: {profile.authentication_strategy}",
            f"{tr(self.language, 'required_capabilities')}: {', '.join(profile.required_capabilities) or tr(self.language, 'no')}",
            f"{tr(self.language, 'limitations')}: {', '.join(profile.known_limitations) or tr(self.language, 'no')}",
            "",
            f"{tr(self.language, 'last_health')}:",
        ]
        if health is None:
            lines.append(tr(self.language, "not_checked"))
        else:
            lines.extend(
                [
                    f"{tr(self.language, 'install')}: {health.installation_status}",
                    f"{tr(self.language, 'auth')}: {health.authentication_status}",
                    f"{tr(self.language, 'access')}: {health.access_status}",
                    f"{tr(self.language, 'health')}: {health.health_status}",
                    f"{tr(self.language, 'capabilities')}: {health.capability_status}",
                    f"{tr(self.language, 'diagnostics')}: {health.diagnostic}",
                ]
            )
        self.detail.setPlainText("\n".join(lines))

    def run_checks(self) -> None:
        for profile in self.registry.profiles():
            self.health_service.check_provider(profile.provider_id)
        self.refresh()


class ProductDiagnosticsTab(QWidget):
    def __init__(self, service: ProductMetricsService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["РњРµС‚СЂРёРєР°", "Р—РЅР°С‡РµРЅРёРµ", "РЎС‚Р°С‚СѓСЃ", "РћСЃРЅРѕРІР°РЅРёРµ"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.routing_table = QTableWidget(0, 6)
        self.routing_table.setHorizontalHeaderLabels(["Р’СЂРµРјСЏ", "Р РµР¶РёРј", "РћС‚РІРµС‚РёР»Рё", "РњРѕР»С‡Р°Р»Рё", "РџСЂРёС‡РёРЅР°", "Р’РµСЂСЃРёСЏ"])
        self.routing_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.routing_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.thread_table = QTableWidget(0, 6)
        self.thread_table.setHorizontalHeaderLabels(["РћР±РЅРѕРІР»РµРЅ", "РўСЂРµРґ", "Р’Р»Р°РґРµР»РµС†", "Р—Р°РґР°С‡Р°", "РўРµРјР°", "РћР¶РёРґР°РµС‚СЃСЏ"])
        self.thread_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.thread_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.question_table = QTableWidget(0, 6)
        self.question_table.setHorizontalHeaderLabels(["Обновлен", "Статус", "Назначено", "Вопрос", "Ответ", "Ответил"])
        self.question_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.question_table.setEditTriggers(QTableWidget.NoEditTriggers)

        accept_question = QPushButton("Принять ответ")
        accept_question.clicked.connect(self.accept_question_answer)
        reopen_question = QPushButton("Вернуть в работу")
        reopen_question.clicked.connect(self.reopen_question)
        question_buttons = QHBoxLayout()
        question_buttons.addWidget(accept_question)
        question_buttons.addWidget(reopen_question)
        question_buttons.addStretch(1)

        refresh = QPushButton("РћР±РЅРѕРІРёС‚СЊ")
        refresh.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Р›РѕРєР°Р»СЊРЅР°СЏ РґРёР°РіРЅРѕСЃС‚РёРєР° РєР°С‡РµСЃС‚РІР°: РјР°СЂС€СЂСѓС‚РёР·Р°С†РёСЏ, РїРѕРІС‚РѕСЂС‹, evidence, РѕС‚РјРµРЅС‹ Рё РЅР°РІС‹РєРё. Р”Р°РЅРЅС‹Рµ РЅРµ РѕС‚РїСЂР°РІР»СЏСЋС‚СЃСЏ РЅР°СЂСѓР¶Сѓ."))
        layout.addWidget(self.metrics_table, 1)
        layout.addWidget(QLabel("РџРѕС‡РµРјСѓ РѕС‚РІРµС‚РёР» СЌС‚РѕС‚ СЃРѕС‚СЂСѓРґРЅРёРє"))
        layout.addWidget(self.routing_table, 1)
        layout.addWidget(QLabel("РђРєС‚РёРІРЅС‹Рµ РІР»Р°РґРµР»СЊС†С‹ СЂР°Р·РіРѕРІРѕСЂРѕРІ"))
        layout.addWidget(self.thread_table, 1)
        layout.addWidget(QLabel("Открытые и закрытые вопросы владельца"))
        layout.addWidget(self.question_table, 1)
        layout.addLayout(question_buttons)
        layout.addWidget(refresh)

    def refresh(self) -> None:
        if self.service is None:
            self.metrics_table.setRowCount(0)
            self.routing_table.setRowCount(0)
            self.thread_table.setRowCount(0)
            self.question_table.setRowCount(0)
            return
        metrics = self.service.metrics()
        self.metrics_table.setRowCount(len(metrics))
        for row_index, metric in enumerate(metrics):
            values = [metric.name, metric.value, metric.status, metric.detail]
            for column, value in enumerate(values):
                self.metrics_table.setItem(row_index, column, QTableWidgetItem(value))

        diagnostics = self.service.recent_routing_diagnostics()
        self.routing_table.setRowCount(len(diagnostics))
        for row_index, diagnostic in enumerate(diagnostics):
            values = [
                diagnostic.created_at,
                diagnostic.participation_mode,
                diagnostic.selected,
                diagnostic.excluded,
                diagnostic.reason,
                diagnostic.router_version,
            ]
            for column, value in enumerate(values):
                self.routing_table.setItem(row_index, column, QTableWidgetItem(value))

        threads = self.service.recent_thread_diagnostics()
        self.thread_table.setRowCount(len(threads))
        for row_index, thread in enumerate(threads):
            values = [
                thread.updated_at,
                thread.thread_id,
                thread.owner,
                thread.active_task_id,
                trim(thread.topic),
                thread.expected_next_actor,
            ]
            for column, value in enumerate(values):
                self.thread_table.setItem(row_index, column, QTableWidgetItem(value))

        questions = self.service.recent_question_diagnostics()
        self.question_table.setRowCount(len(questions))
        for row_index, question in enumerate(questions):
            values = [
                question.updated_at,
                question.status,
                question.assigned,
                trim(question.question),
                question.answer_message_id,
                question.answered_by,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, question.question_id)
                self.question_table.setItem(row_index, column, item)

    def _selected_question_id(self) -> str | None:
        row = self.question_table.currentRow()
        if row < 0:
            return None
        item = self.question_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def accept_question_answer(self) -> None:
        question_id = self._selected_question_id()
        if not question_id or self.service is None:
            return
        self.service.accept_question_answer(question_id)
        self.refresh()

    def reopen_question(self) -> None:
        question_id = self._selected_question_id()
        if not question_id or self.service is None:
            return
        self.service.reopen_question(question_id)
        self.refresh()


class AuditTab(QWidget):
    def __init__(self, service: ManagementService, language: str, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language
        self.action_filter = QLineEdit()
        self.action_filter.setPlaceholderText(tr(language, "filter_audit"))
        self.action_filter.textChanged.connect(self.refresh)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "time"),
                tr(language, "actor"),
                tr(language, "action"),
                tr(language, "object_type"),
                tr(language, "object_id"),
                tr(language, "previous"),
                tr(language, "new"),
                tr(language, "reason"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout(self)
        layout.addWidget(self.action_filter)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        text = self.action_filter.text().strip().lower()
        rows = self.service.list_audit_events()
        if text:
            rows = [
                row
                for row in rows
                if text in f"{row['action']} {row['object_type']} {row['object_id']} {row['reason']}".lower()
            ]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["created_at"],
                row["actor"],
                row["action"],
                row["object_type"],
                row["object_id"],
                trim(str(row["previous_value"] or "")),
                trim(str(row["new_value"] or "")),
                str(row["reason"] or ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))


class AddEmployeeWizard(QWizard):
    def __init__(
        self,
        service: ManagementService,
        provider_health_service: ProviderHealthService,
        provider_provisioning_service: ProviderProvisioningService,
        language: str = "ru",
        avatar_dir: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.provider_health_service = provider_health_service
        self.provider_provisioning_service = provider_provisioning_service
        self.language = language
        self.avatar_dir = avatar_dir
        self.setWindowTitle(tr(language, "add_employee"))
        self.setOption(QWizard.NoBackButtonOnStartPage, False)
        self.identity = IdentityPage(service, language, avatar_dir)
        self.roles = RolesPage(service, language)
        self.provider = ProviderPage(provider_health_service, language)
        self.persona = PersonaPage(language)
        self.permissions = PermissionsPage(service, language)
        self.review = ReviewPage(self)
        for page in (self.identity, self.roles, self.provider, self.persona, self.permissions, self.review):
            self.addPage(page)
        self.setButtonText(QWizard.CustomButton1, tr(language, "dry_run"))
        self.setOption(QWizard.HaveCustomButton1, True)
        self.customButtonClicked.connect(self.dry_run)

    def profile(self) -> AgentProfile:
        return AgentProfile(
            agent_id=self.identity.agent_id.text().strip(),
            display_name=self.identity.display_name.text().strip(),
            description=self.identity.description.toPlainText().strip(),
            lifecycle_state=self.identity.lifecycle.currentData(),
            provider_id=self.provider.provider.currentData(),
            persona_id=self.persona.persona.currentText().strip() or None,
            avatar_path=self.identity.selected_avatar_path(),
        )

    def selected_roles(self) -> list[str]:
        return self.roles.selected_roles()

    def selected_permissions(self) -> list[str]:
        return self.permissions.selected_grants()

    def dry_run(self) -> None:
        preview = self.service.create_agent(
            self.profile(),
            self.selected_roles(),
            self.selected_permissions(),
            reason="dry run",
            dry_run=True,
        )
        QMessageBox.information(self, tr(self.language, "check"), format_preview(preview, self.language))

    def accept(self) -> None:
        try:
            preview = self.service.create_agent(
                self.profile(),
                self.selected_roles(),
                self.selected_permissions(),
                reason="created from Director Console",
                dry_run=False,
            )
        except Exception as exc:
            QMessageBox.warning(self, tr(self.language, "cannot_create"), friendly_error(str(exc), self.language))
            return
        if not preview.ok:
            QMessageBox.warning(self, tr(self.language, "cannot_create"), format_preview(preview, self.language))
            return
        super().accept()


class IdentityPage(QWizardPage):
    def __init__(self, service: ManagementService, language: str, avatar_dir: Path | None = None) -> None:
        super().__init__()
        self.service = service
        self.language = language
        self.avatar_dir = avatar_dir
        self.setTitle(tr(language, "basic_data"))
        self.display_name = QLineEdit()
        self.description = QTextEdit()
        self.description.setFixedHeight(80)
        self.avatar = QLineEdit()
        self.avatar_choice = QComboBox()
        self._load_avatar_choices()
        self.avatar_choice.currentIndexChanged.connect(self._apply_avatar_choice)
        browse_avatar = QPushButton("...")
        browse_avatar.setToolTip(tr(language, "avatar"))
        browse_avatar.clicked.connect(self._browse_avatar)
        avatar_row = QHBoxLayout()
        avatar_row.addWidget(self.avatar_choice, 1)
        avatar_row.addWidget(browse_avatar)
        self.agent_id = QLineEdit()
        self.lifecycle = QComboBox()
        for state in ("DRAFT", "ACTIVE", "SUSPENDED", "DISABLED", "ARCHIVED"):
            self.lifecycle.addItem(status_label(language, state), state)
        self.lifecycle.setCurrentIndex(0)
        generate = QPushButton(tr(language, "generate_id"))
        generate.clicked.connect(self.generate_id)
        self.display_name.textChanged.connect(self.generate_id_if_empty)
        row = QHBoxLayout()
        row.addWidget(self.agent_id)
        row.addWidget(generate)
        form = QFormLayout(self)
        form.addRow(tr(language, "name"), self.display_name)
        form.addRow(tr(language, "agent_id"), row)
        form.addRow(tr(language, "description"), self.description)
        form.addRow(tr(language, "avatar"), avatar_row)
        form.addRow("", self.avatar)
        form.addRow(tr(language, "status"), self.lifecycle)
        self._apply_avatar_choice()

    def generate_id_if_empty(self) -> None:
        if not self.agent_id.text().strip():
            self.generate_id()

    def generate_id(self) -> None:
        self.agent_id.setText(self.service.generate_agent_id(self.display_name.text()))

    def selected_avatar_path(self) -> str | None:
        return self.avatar.text().strip() or None

    def _load_avatar_choices(self) -> None:
        self.avatar_choice.addItem(tr(self.language, "not_set"), "")
        if self.avatar_dir and self.avatar_dir.exists():
            for path in sorted(self.avatar_dir.glob("*.png")):
                if path.name.startswith("avatar-sheet"):
                    continue
                self.avatar_choice.addItem(QIcon(str(path)), self._avatar_label(path, self.language), str(path))

    def _apply_avatar_choice(self) -> None:
        value = self.avatar_choice.currentData()
        self.avatar.setText(str(value or ""))

    def _browse_avatar(self) -> None:
        start = str(self.avatar_dir) if self.avatar_dir else ""
        selected, _ = QFileDialog.getOpenFileName(
            self,
            tr(self.language, "avatar"),
            start,
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if selected:
            self.avatar.setText(selected)

    @staticmethod
    def _avatar_label(path: Path, language: str = "ru") -> str:
        if path.stem.startswith("avatar-"):
            parts = path.stem.split("-")
            number = parts[1] if len(parts) > 1 else ""
            words = parts[2:]
            vocabulary = {
                "ru": {
                    "woman": "Р¶РµРЅС‰РёРЅР°",
                    "man": "РјСѓР¶С‡РёРЅР°",
                    "realistic": "СЂРµР°Р»РёР·Рј",
                    "cartoon": "РјСѓР»СЊС‚",
                    "cat": "РєРѕС‚",
                    "dog": "СЃРѕР±Р°РєР°",
                    "tabby": "РїРѕР»РѕСЃР°С‚С‹Р№",
                    "ginger": "СЂС‹Р¶РёР№",
                    "golden": "СЂРµС‚СЂРёРІРµСЂ",
                    "corgi": "РєРѕСЂРіРё",
                    "reaction": "РјРµРј",
                },
                "uk": {
                    "woman": "Р¶С–РЅРєР°",
                    "man": "С‡РѕР»РѕРІС–Рє",
                    "realistic": "СЂРµР°Р»С–Р·Рј",
                    "cartoon": "РјСѓР»СЊС‚",
                    "cat": "РєС–С‚",
                    "dog": "СЃРѕР±Р°РєР°",
                    "tabby": "СЃРјСѓРіР°СЃС‚РёР№",
                    "ginger": "СЂСѓРґРёР№",
                    "golden": "СЂРµС‚СЂРёРІРµСЂ",
                    "corgi": "РєРѕСЂРіС–",
                    "reaction": "РјРµРј",
                },
                "en": {},
            }
            translated = [vocabulary.get(language, vocabulary["ru"]).get(word, word) for word in words]
            return f"{number} - {', '.join(translated)}".strip(" -")
        labels = {
            "ru": {
                "realistic-female": "Р РµР°Р»РёР·Рј: Р¶РµРЅС‰РёРЅР°",
                "realistic-male": "Р РµР°Р»РёР·Рј: РјСѓР¶С‡РёРЅР°",
                "cartoon-female": "РњСѓР»СЊС‚: Р¶РµРЅС‰РёРЅР°",
                "cartoon-male": "РњСѓР»СЊС‚: РјСѓР¶С‡РёРЅР°",
            },
            "uk": {
                "realistic-female": "Р РµР°Р»С–Р·Рј: Р¶С–РЅРєР°",
                "realistic-male": "Р РµР°Р»С–Р·Рј: С‡РѕР»РѕРІС–Рє",
                "cartoon-female": "РњСѓР»СЊС‚: Р¶С–РЅРєР°",
                "cartoon-male": "РњСѓР»СЊС‚: С‡РѕР»РѕРІС–Рє",
            },
            "en": {
                "realistic-female": "Realistic: woman",
                "realistic-male": "Realistic: man",
                "cartoon-female": "Cartoon: woman",
                "cartoon-male": "Cartoon: man",
            },
        }
        return labels.get(language, labels["ru"]).get(path.stem, path.stem.replace("-", " ").title())

    def validatePage(self) -> bool:
        if not self.display_name.text().strip():
            QMessageBox.warning(self, tr(self.language, "check_data"), tr(self.language, "name_required"))
            return False
        if not self.agent_id.text().strip().startswith("agent-"):
            QMessageBox.warning(self, tr(self.language, "check_data"), tr(self.language, "agent_id_required"))
            return False
        return True


class RolesPage(QWizardPage):
    def __init__(self, service: ManagementService, language: str) -> None:
        super().__init__()
        self.service = service
        self.language = language
        self.setTitle(tr(language, "role"))
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.MultiSelection)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        for role in sorted(ROLE_IDS):
            item = QListWidgetItem(role_label(language, role))
            item.setData(Qt.UserRole, role)
            self.list.addItem(item)
        self.list.itemSelectionChanged.connect(self.update_preview)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(language, "select_roles")))
        layout.addWidget(self.list)
        layout.addWidget(QLabel(tr(language, "inherited_permissions")))
        layout.addWidget(self.preview)

    def selected_roles(self) -> list[str]:
        return [str(item.data(Qt.UserRole)) for item in self.list.selectedItems()]

    def update_preview(self) -> None:
        roles = self.selected_roles()
        permissions = sorted(self.service.inherited_permissions(roles))
        lines = [
            f"{tr(self.language, 'roles')}: {', '.join(role_label(self.language, role) for role in roles) or tr(self.language, 'not_set')}",
            "",
            f"{tr(self.language, 'inherited_permissions')}:",
            *[permission_label(self.language, permission) for permission in permissions],
        ]
        self.preview.setPlainText("\n".join(lines))

    def validatePage(self) -> bool:
        if not self.selected_roles():
            QMessageBox.warning(self, tr(self.language, "role"), tr(self.language, "role_required"))
            return False
        return True


class ProviderPage(QWizardPage):
    def __init__(self, provider_health_service: ProviderHealthService, language: str) -> None:
        super().__init__()
        self.provider_health_service = provider_health_service
        self.language = language
        self.setTitle(tr(language, "provider"))
        self.provider = QComboBox()
        self.status = QLabel()
        for profile in provider_health_service.registry.profiles():
            self.provider.addItem(profile.display_name, profile.provider_id)
        self.provider.currentIndexChanged.connect(self.refresh_status)
        layout = QFormLayout(self)
        layout.addRow(tr(language, "provider"), self.provider)
        layout.addRow(tr(language, "status"), self.status)
        self.refresh_status()

    def refresh_status(self) -> None:
        provider_id = str(self.provider.currentData())
        health = self.provider_health_service.latest_health(provider_id) or self.provider_health_service.check_provider(provider_id)
        self.status.setText(
            f"install={health.installation_status}; auth={health.authentication_status}; "
            f"access={health.access_status}; health={health.health_status}"
        )


class PersonaPage(QWizardPage):
    def __init__(self, language: str) -> None:
        super().__init__()
        self.setTitle(tr(language, "persona"))
        self.persona = QComboBox()
        self.persona.addItems(["neutral_engineer", "roman_2050", "petr_2050", "document_control", "qa_reviewer"])
        layout = QFormLayout(self)
        layout.addRow(tr(language, "persona"), self.persona)


class PermissionsPage(QWizardPage):
    def __init__(self, service: ManagementService, language: str) -> None:
        super().__init__()
        self.service = service
        self.language = language
        self.setTitle(tr(language, "permissions"))
        self.checks: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(language, "permissions_note")))
        for permission in sorted(PERMISSIONS):
            check = QCheckBox(permission_label(language, permission))
            if permission in {"MANAGE_EMPLOYEES", "GRANT_APPROVAL", "MANAGE_STANDARDS"}:
                check.setEnabled(False)
            self.checks[permission] = check
            layout.addWidget(check)
        layout.addStretch(1)

    def selected_grants(self) -> list[str]:
        return [permission for permission, check in self.checks.items() if check.isChecked()]


class ReviewPage(QWizardPage):
    def __init__(self, wizard: AddEmployeeWizard) -> None:
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle(tr(wizard.language, "review"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(wizard.language, "review_config")))
        layout.addWidget(self.preview)

    def initializePage(self) -> None:
        preview = self.wizard_ref.service.create_agent(
            self.wizard_ref.profile(),
            self.wizard_ref.selected_roles(),
            self.wizard_ref.selected_permissions(),
            reason="preview",
            dry_run=True,
        )
        lines = [
            f"{tr(self.wizard_ref.language, 'employee')}: {self.wizard_ref.profile().display_name}",
            f"{tr(self.wizard_ref.language, 'agent_id')}: {self.wizard_ref.profile().agent_id}",
            f"{tr(self.wizard_ref.language, 'roles')}: {', '.join(role_label(self.wizard_ref.language, role) for role in self.wizard_ref.selected_roles())}",
            f"{tr(self.wizard_ref.language, 'provider')}: {PROVIDER_LABELS.get(self.wizard_ref.profile().provider_id, self.wizard_ref.profile().provider_id)}",
            f"{tr(self.wizard_ref.language, 'persona')}: {self.wizard_ref.profile().persona_id}",
            f"{tr(self.wizard_ref.language, 'status')}: {status_label(self.wizard_ref.language, self.wizard_ref.profile().lifecycle_state)}",
            "",
            format_preview(preview, self.wizard_ref.language),
        ]
        self.preview.setPlainText("\n".join(lines))


class EditEmployeeDialog(QDialog):
    def __init__(
        self,
        service: ManagementService,
        agent_id: str,
        language: str = "ru",
        avatar_dir: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.agent_id = agent_id
        self.language = language
        self.avatar_dir = avatar_dir
        self.employee = service.get_employee(agent_id)
        self.row = service.database.get_agent_profile(agent_id)
        if self.employee is None or self.row is None:
            raise ValueError("unknown employee")
        self.setWindowTitle(tr(language, "edit"))
        self.resize(760, 620)
        self.display_name = QLineEdit(self.employee.display_name)
        self.description = QTextEdit(str(self.row["description"]))
        self.description.setFixedHeight(90)
        self.avatar = QLineEdit(str(self.row["avatar_path"] or ""))
        self.avatar_choice = QComboBox()
        self._load_avatar_choices()
        current_avatar = self.avatar.text().strip()
        if current_avatar:
            index = self.avatar_choice.findData(current_avatar)
            if index >= 0:
                self.avatar_choice.setCurrentIndex(index)
        self.avatar_choice.currentIndexChanged.connect(self._apply_avatar_choice)
        browse_avatar = QPushButton("...")
        browse_avatar.setToolTip(tr(language, "avatar"))
        browse_avatar.clicked.connect(self._browse_avatar)
        avatar_row = QHBoxLayout()
        avatar_row.addWidget(self.avatar_choice, 1)
        avatar_row.addWidget(browse_avatar)
        self.provider = QComboBox()
        for provider in sorted(PROVIDER_IDS):
            self.provider.addItem(PROVIDER_LABELS.get(provider, provider), provider)
        self.provider.setCurrentIndex(max(0, self.provider.findData(self.employee.provider_id)))
        self.persona = QComboBox()
        self.persona.addItems(["neutral_engineer", "roman_2050", "petr_2050", "document_control", "qa_reviewer"])
        if self.employee.persona_id:
            self.persona.setCurrentIndex(max(0, self.persona.findText(self.employee.persona_id)))
        self.roles = QListWidget()
        self.roles.setSelectionMode(QListWidget.MultiSelection)
        for role in sorted(ROLE_IDS):
            item = QListWidgetItem(role_label(language, role))
            item.setData(Qt.UserRole, role)
            self.roles.addItem(item)
            if role in self.employee.roles:
                item.setSelected(True)
        self.permissions = QListWidget()
        self.permissions.setSelectionMode(QListWidget.MultiSelection)
        self.denies = QListWidget()
        self.denies.setSelectionMode(QListWidget.MultiSelection)
        for permission in sorted(PERMISSIONS):
            item = QListWidgetItem(permission_label(language, permission))
            item.setData(Qt.UserRole, permission)
            if permission in {"MANAGE_EMPLOYEES", "GRANT_APPROVAL", "MANAGE_STANDARDS"}:
                item.setFlags(Qt.NoItemFlags)
            self.permissions.addItem(item)
            if permission in self.employee.direct_permissions:
                item.setSelected(True)
            deny_item = QListWidgetItem(permission_label(language, permission))
            deny_item.setData(Qt.UserRole, permission)
            self.denies.addItem(deny_item)
            if permission in self.employee.permission_denies:
                deny_item.setSelected(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow(tr(language, "agent_id"), QLabel(self.agent_id))
        form.addRow(tr(language, "name"), self.display_name)
        form.addRow(tr(language, "description"), self.description)
        form.addRow(tr(language, "avatar"), avatar_row)
        form.addRow("", self.avatar)
        form.addRow(tr(language, "provider"), self.provider)
        form.addRow(tr(language, "persona"), self.persona)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel(tr(language, "roles")))
        layout.addWidget(self.roles)
        layout.addWidget(QLabel(tr(language, "direct_grants")))
        layout.addWidget(self.permissions)
        layout.addWidget(QLabel(tr(language, "direct_denies")))
        layout.addWidget(self.denies)
        layout.addWidget(buttons)

    def selected_roles(self) -> list[str]:
        return [str(item.data(Qt.UserRole)) for item in self.roles.selectedItems()]

    def selected_permissions(self) -> list[str]:
        return [str(item.data(Qt.UserRole)) for item in self.permissions.selectedItems()]

    def selected_denies(self) -> list[str]:
        return [str(item.data(Qt.UserRole)) for item in self.denies.selectedItems()]

    def _load_avatar_choices(self) -> None:
        self.avatar_choice.addItem(tr(self.language, "not_set"), "")
        if self.avatar_dir and self.avatar_dir.exists():
            for path in sorted(self.avatar_dir.glob("*.png")):
                if path.name.startswith("avatar-sheet"):
                    continue
                self.avatar_choice.addItem(QIcon(str(path)), IdentityPage._avatar_label(path, self.language), str(path))

    def _apply_avatar_choice(self) -> None:
        value = self.avatar_choice.currentData()
        self.avatar.setText(str(value or ""))

    def _browse_avatar(self) -> None:
        start = str(self.avatar_dir) if self.avatar_dir else ""
        selected, _ = QFileDialog.getOpenFileName(
            self,
            tr(self.language, "avatar"),
            start,
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if selected:
            self.avatar.setText(selected)

    def save(self) -> None:
        try:
            preview = self.service.update_employee(
                self.agent_id,
                display_name=self.display_name.text().strip(),
                description=self.description.toPlainText().strip(),
                provider_id=str(self.provider.currentData()),
                persona_id=self.persona.currentText().strip() or None,
                avatar_path=self.avatar.text().strip() or None,
                roles=self.selected_roles(),
                permission_grants=self.selected_permissions(),
                permission_denies=self.selected_denies(),
                expected_updated_at=str(self.row["updated_at"]),
                reason="edited from Director Console",
            )
        except Exception as exc:
            QMessageBox.warning(self, tr(self.language, "not_saved"), friendly_error(str(exc), self.language))
            return
        if not preview.ok:
            QMessageBox.warning(self, tr(self.language, "not_saved"), format_preview(preview, self.language))
            return
        self.accept()


def format_employee_detail(
    employee: EmployeeSummary,
    service: ManagementService,
    readiness: str | None = None,
    language: str = "ru",
) -> str:
    inherited = sorted(service.inherited_permissions(employee.roles))
    roles = [role_label(language, role) for role in employee.roles]
    inherited_permissions = [permission_label(language, permission) for permission in inherited]
    direct_permissions = [permission_label(language, permission) for permission in employee.direct_permissions]
    denied_permissions = [permission_label(language, permission) for permission in employee.permission_denies]
    effective_permissions = [permission_label(language, permission) for permission in employee.effective_permissions]
    return "\n".join(
        [
            tr(language, "identity").upper(),
            f"{tr(language, 'name')}: {employee.display_name}",
            f"{tr(language, 'agent_id')}: {employee.agent_id}",
            f"{tr(language, 'status')}: {status_label(language, employee.lifecycle_state)}",
            f"{tr(language, 'time')}: {employee.updated_at}",
            "",
            tr(language, "organization").upper(),
            f"{tr(language, 'roles')}: {', '.join(roles) or tr(language, 'no')}",
            f"{tr(language, 'provider')}: {PROVIDER_LABELS.get(employee.provider_id, employee.provider_id)}",
            f"{tr(language, 'persona')}: {employee.persona_id or tr(language, 'not_set')}",
            "",
            tr(language, "permissions").upper(),
            f"{tr(language, 'inherited_permissions')}: {', '.join(inherited_permissions) or tr(language, 'no')}",
            f"{tr(language, 'direct_grants')}: {', '.join(direct_permissions) or tr(language, 'no')}",
            f"{tr(language, 'direct_denies')}: {', '.join(denied_permissions) or tr(language, 'no')}",
            f"{tr(language, 'effective_permissions')}: {', '.join(effective_permissions) or tr(language, 'no')}",
            "",
            tr(language, "configuration_health").upper(),
            "\n".join(employee.warnings or [tr(language, "no_warnings")]),
            "",
            tr(language, "execution_eligibility").upper(),
            readiness_label(language, readiness or employee.availability),
        ]
    )


def format_preview(preview, language: str = "ru") -> str:
    errors = [friendly_error(error, language) for error in preview.errors]
    lines = [
        f"{tr(language, 'action')}: {preview.action}",
        f"{tr(language, 'status')}: {tr(language, 'ok') if preview.ok else tr(language, 'rejected')}",
        "",
        f"{tr(language, 'database_rows')}:",
        *(preview.database_rows or [tr(language, "no")]),
        "",
        f"{tr(language, 'files')}:",
        *(preview.files or [tr(language, "no")]),
        "",
        f"{tr(language, 'warnings')}:",
        *(preview.warnings or [tr(language, "no")]),
        "",
        f"{tr(language, 'errors')}:",
        *(errors or [tr(language, "no")]),
    ]
    return "\n".join(lines)


def friendly_error(text: str, language: str = "ru") -> str:
    mapping = {
        "ru": {
            "owner_authority_required": "РўСЂРµР±СѓСЋС‚СЃСЏ РїСЂР°РІР° РІР»Р°РґРµР»СЊС†Р° РѕСЂРіР°РЅРёР·Р°С†РёРё.",
            "duplicate_agent_id": "РўР°РєРѕР№ ID СЃРѕС‚СЂСѓРґРЅРёРєР° СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓРµС‚.",
            "active_employee_requires_available_provider": "РђРєС‚РёРІРЅРѕРјСѓ СЃРѕС‚СЂСѓРґРЅРёРєСѓ РЅСѓР¶РµРЅ РґРѕСЃС‚СѓРїРЅС‹Р№ РїСЂРѕРІР°Р№РґРµСЂ.",
            "optimistic_lock_conflict": "РџСЂРѕС„РёР»СЊ СѓР¶Рµ РёР·РјРµРЅРёР»СЃСЏ. РћР±РЅРѕРІРёС‚Рµ РєР°СЂС‚РѕС‡РєСѓ Рё РїРѕРІС‚РѕСЂРёС‚Рµ.",
            "FOREIGN KEY constraint failed": tr(language, "foreign_key_error"),
            "invalid_role": tr(language, "unknown_role"),
            "unknown_role": tr(language, "unknown_role"),
            "invalid_provider": tr(language, "unknown_provider"),
            "unknown_agent_id": tr(language, "unknown_agent"),
            "empty_display_name": tr(language, "empty_display_name"),
            "agent_id_must_be_stable_agent_id": tr(language, "agent_id_required"),
        },
        "uk": {
            "owner_authority_required": "РџРѕС‚СЂС–Р±РЅС– РїСЂР°РІР° РІР»Р°СЃРЅРёРєР° РѕСЂРіР°РЅС–Р·Р°С†С–С—.",
            "duplicate_agent_id": "РўР°РєРёР№ ID СЃРїС–РІСЂРѕР±С–С‚РЅРёРєР° РІР¶Рµ С–СЃРЅСѓС”.",
            "active_employee_requires_available_provider": "РђРєС‚РёРІРЅРѕРјСѓ СЃРїС–РІСЂРѕР±С–С‚РЅРёРєСѓ РїРѕС‚СЂС–Р±РµРЅ РґРѕСЃС‚СѓРїРЅРёР№ РїСЂРѕРІР°Р№РґРµСЂ.",
            "optimistic_lock_conflict": "РџСЂРѕС„С–Р»СЊ СѓР¶Рµ Р·РјС–РЅРёРІСЃСЏ. РћРЅРѕРІС–С‚СЊ РєР°СЂС‚РєСѓ С– РїРѕРІС‚РѕСЂС–С‚СЊ.",
            "FOREIGN KEY constraint failed": tr(language, "foreign_key_error"),
            "invalid_role": tr(language, "unknown_role"),
            "unknown_role": tr(language, "unknown_role"),
            "invalid_provider": tr(language, "unknown_provider"),
            "unknown_agent_id": tr(language, "unknown_agent"),
            "empty_display_name": tr(language, "empty_display_name"),
            "agent_id_must_be_stable_agent_id": tr(language, "agent_id_required"),
        },
        "en": {
            "owner_authority_required": "Organization owner permissions are required.",
            "duplicate_agent_id": "This employee ID already exists.",
            "active_employee_requires_available_provider": "An active employee needs an available provider.",
            "optimistic_lock_conflict": "The profile has already changed. Refresh and try again.",
            "FOREIGN KEY constraint failed": tr(language, "foreign_key_error"),
            "invalid_role": tr(language, "unknown_role"),
            "unknown_role": tr(language, "unknown_role"),
            "invalid_provider": tr(language, "unknown_provider"),
            "unknown_agent_id": tr(language, "unknown_agent"),
            "empty_display_name": tr(language, "empty_display_name"),
            "agent_id_must_be_stable_agent_id": tr(language, "agent_id_required"),
        },
    }
    selected = mapping.get(language, mapping["ru"])
    for key, value in selected.items():
        if key in text:
            return value
    return text.replace("_", " ")


def trim(text: str, limit: int = 160) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 3] + "..."
