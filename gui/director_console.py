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
    QSpinBox,
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
from core.avatar_catalog import list_avatar_files
from core.director_service import DirectorService
from core.employee_identity import generate_identity
from core.finding_service import FINDING_CONFIDENCE, FINDING_SEVERITIES, FindingService
from core.management_service import EmployeeSummary, ManagementService
from core.knowledge_service import KNOWLEDGE_STATUSES, SOURCE_AUTHORITIES, KnowledgeService
from core.learning_evidence_service import LearningEvidenceService
from core.learning_manager_service import LearningManagerService
from core.provider_service import ProviderHealthService, ProviderProvisioningService, ProviderRegistry
from core.provider_lifecycle_service import ProviderLifecycleService
from core.secure_storage import SecureStorageUnavailable, WindowsCredentialStore
from core.product_metrics_service import ProductMetricsService
from core.skill_progress_service import SkillProgressService
from core.skill_package_service import SkillPackageService
from core.standards_service import MANDATORY_LEVELS, STANDARD_AUTHORITIES, StandardsService
from core.universal_platform_service import UniversalPlatformService
from gui.localization import catalog_label, catalog_purpose, permission_label, readiness_label, role_label, status_label, team_size_label, tr, workflow_label
from gui.dialog_chrome import apply_team_dialog_chrome


STATUS_LABELS = {
    "DRAFT": "Черновик",
    "ACTIVE": "Активен",
    "SUSPENDED": "Приостановлен",
    "DISABLED": "Отключен",
    "ARCHIVED": "Архив",
}

PROVIDER_LABELS = {
    "CODEX_CLI": "Codex CLI",
    "GEMINI_CLI": "Gemini CLI",
    "CLAUDE_CLI": "Claude CLI",
    "FUTURE_PROVIDER": "Будущий provider",
    "UNAVAILABLE": "Не настроен",
}

PERSONA_PRESETS = {
    "neutral_professional": {"ru": "Нейтральный профессионал", "uk": "Нейтральний професіонал", "en": "Neutral professional"},
    "concise_engineer": {"ru": "Лаконичный инженер", "uk": "Лаконічний інженер", "en": "Concise engineer"},
    "quality_reviewer": {"ru": "Технический рецензент", "uk": "Технічний рецензент", "en": "Technical reviewer"},
    "document_specialist": {"ru": "Специалист по документам", "uk": "Фахівець із документів", "en": "Document specialist"},
    "project_coordinator": {"ru": "Координатор проекта", "uk": "Координатор проєкту", "en": "Project coordinator"},
}


def fill_persona_combo(combo: QComboBox, language: str) -> None:
    for persona_id, labels in PERSONA_PRESETS.items():
        combo.addItem(labels.get(language, labels["en"]), persona_id)


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
        universal_platform_service: UniversalPlatformService | None = None,
        language: str = "ru",
        avatar_dir: str | Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self, minimum_width=920)
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
        self.universal_platform_service = universal_platform_service
        self.language = language
        self.avatar_dir = Path(avatar_dir) if avatar_dir else None
        self.setWindowTitle("Команда")
        self.resize(1120, 760)
        self.tabs = QTabWidget()

        self.overview_tab = OverviewTab(management_service, provider_health_service, self)
        self.employee_tab = EmployeesTab(management_service, provider_health_service, provider_provisioning_service, language, self.avatar_dir, self)
        self.roles_tab = RolesTab(management_service, language, self)
        self.permissions_tab = PermissionsTab(management_service, language, self)
        self.providers_tab = ProvidersTab(provider_registry, provider_health_service, provider_provisioning_service, management_service, language, self)
        self.skills_tab = SkillProgressTab(skill_progress_service, skill_package_service, management_service, language, self)
        learning_evidence = LearningEvidenceService(management_service.database)
        self.learning_tab = LearningEvidenceTab(
            learning_evidence,
            language,
            self,
            LearningManagerService(management_service.database, learning_evidence, skill_package_service),
        )
        self.knowledge_tab = KnowledgeTab(knowledge_service, self)
        self.standards_tab = StandardsTab(standards_service, self)
        self.artifacts_tab = ArtifactsTab(artifact_service, self)
        self.findings_tab = FindingsTab(finding_service, self)
        self.diagnostics_tab = ProductDiagnosticsTab(product_metrics_service, self)
        self.audit_tab = AuditTab(management_service, language, self)
        self.universal_tab = UniversalPlatformTab(universal_platform_service, self)
        self.director_plans_tab = DirectorPlansTab(DirectorService(management_service.database), language, self)

        self.tabs.addTab(self.overview_tab, tr(language, "overview"))
        self.tabs.addTab(self.universal_tab, tr(language, "organization"))
        self.tabs.addTab(
            self.director_plans_tab,
            {"ru": "Планы", "uk": "Плани", "en": "Plans"}.get(language, "Plans"),
        )
        self.tabs.addTab(self.employee_tab, tr(language, "employees"))
        self.tabs.addTab(self.roles_tab, tr(language, "roles"))
        self.tabs.addTab(self.permissions_tab, tr(language, "permissions"))
        self.tabs.addTab(self.providers_tab, tr(language, "providers"))
        self.tabs.addTab(self.skills_tab, tr(language, "skills"))
        self.tabs.addTab(
            self.learning_tab,
            {"ru": "Развитие", "uk": "Розвиток", "en": "Development"}.get(language, "Development"),
        )
        self.tabs.addTab(self.knowledge_tab, tr(language, "knowledge"))
        self.tabs.addTab(self.standards_tab, tr(language, "standards"))
        self.tabs.addTab(self.artifacts_tab, tr(language, "artifacts"))
        self.tabs.addTab(self.findings_tab, tr(language, "findings"))
        self.tabs.addTab(self.diagnostics_tab, tr(language, "diagnostics"))
        self.tabs.addTab(self.audit_tab, tr(language, "audit"))

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        header = QLabel(tr(language, "organization_owner"))
        header.setObjectName("sectionTitle")
        layout.addWidget(header)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(close)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.overview_tab.refresh()
        self.universal_tab.refresh()
        self.director_plans_tab.refresh()
        self.employee_tab.refresh()
        self.roles_tab.refresh()
        self.permissions_tab.refresh()
        self.providers_tab.refresh()
        self.skills_tab.refresh()
        self.learning_tab.refresh()
        self.knowledge_tab.refresh()
        self.standards_tab.refresh()
        self.artifacts_tab.refresh()
        self.findings_tab.refresh()
        self.diagnostics_tab.refresh()
        self.audit_tab.refresh()


class DirectorPlansTab(QWidget):
    def __init__(self, service: DirectorService, language: str = "ru", parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language
        copy = {
            "ru": ("Цель", "Организация", "Сформировать план", "Планы", "Директор", "Статус", "Заданий", "Подробности"),
            "uk": ("Мета", "Організація", "Сформувати план", "Плани", "Керівник", "Статус", "Завдань", "Подробиці"),
            "en": ("Goal", "Organization", "Create plan", "Plans", "Director", "Status", "Assignments", "Details"),
        }.get(language, ("Goal", "Organization", "Create plan", "Plans", "Director", "Status", "Assignments", "Details"))
        goal_label, organization_label, create_label, plans_label, director_label, status_label_text, assignments_label, details_label = copy
        self.organization = QComboBox()
        self.goal = QTextEdit()
        self.goal.setMaximumHeight(88)
        create = QPushButton(create_label)
        create.clicked.connect(self._create_plan)
        form = QFormLayout()
        form.addRow(organization_label, self.organization)
        form.addRow(goal_label, self.goal)
        form.addRow("", create)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([plans_label, director_label, status_label_text, assignments_label, organization_label])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel(plans_label))
        layout.addWidget(self.table, 1)
        layout.addWidget(QLabel(details_label))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        selected = self.organization.currentData()
        self.organization.clear()
        for row in self.service.database.list_organizations():
            if str(row["status"]).upper() == "ACTIVE":
                self.organization.addItem(str(row["name"]), str(row["id"]))
        index = self.organization.findData(selected)
        if index >= 0:
            self.organization.setCurrentIndex(index)
        plans = self.service.list_plans()
        self.table.setRowCount(len(plans))
        for row_index, plan in enumerate(plans):
            organization = next(
                (row for row in self.service.database.list_organizations() if str(row["id"]) == plan.organization_id),
                None,
            )
            values = [
                plan.goal,
                plan.director_name,
                workflow_label(self.language, plan.status),
                str(len(plan.assignments)),
                str(organization["name"]) if organization is not None else plan.organization_id,
            ]
            detail = "\n".join(
                [
                    f"{plan.director_name}: {plan.goal}",
                    f"{workflow_label(self.language, plan.status)}",
                    f"Missing roles: {', '.join(plan.missing_roles) or '-'}",
                    f"Owner approval: {'yes' if plan.owner_approval_required else 'no'}",
                    "",
                    *[
                        f"{item.sequence_no}. {item.employee_name} · {item.position} · {workflow_label(self.language, item.status)}"
                        for item in plan.assignments
                    ],
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, detail)
                self.table.setItem(row_index, column, item)

    def _create_plan(self) -> None:
        organization_id = self.organization.currentData()
        goal = self.goal.toPlainText().strip()
        if not organization_id or not goal:
            return
        try:
            self.service.create_plan(str(organization_id), goal)
        except ValueError as exc:
            messages = {
                "director_not_assigned": {
                    "ru": "В организации не назначен директор или руководитель.",
                    "uk": "В організації не призначено директора або керівника.",
                    "en": "No director or organization manager is assigned.",
                },
                "goal_required": {
                    "ru": "Введите цель.", "uk": "Введіть мету.", "en": "Enter a goal.",
                },
            }
            QMessageBox.warning(self, "Team2050", messages.get(str(exc), {}).get(self.language, str(exc)))
            return
        self.goal.clear()
        self.refresh()

    def _show_detail(self) -> None:
        items = self.table.selectedItems()
        if items:
            self.detail.setPlainText(str(items[0].data(Qt.UserRole) or ""))


class UniversalPlatformTab(QWidget):
    """No-code catalog and operational organization activation surface."""

    def __init__(self, service: UniversalPlatformService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = getattr(parent, "language", "ru")
        self.professions = QListWidget()
        self.organizations = QListWidget()
        self.templates = QListWidget()
        self.template_search = QLineEdit()
        self.template_search.setPlaceholderText({"ru": "Поиск пресетов: разработка, кухня, маленькая команда...", "uk": "Пошук пресетів: розробка, кухня, мала команда...", "en": "Search presets: development, culinary, small team..."}[self.language])
        self.organization_dashboard = QTextEdit()
        self.organization_dashboard.setReadOnly(True)
        self.organization_dashboard.setMinimumHeight(150)
        self.organization_dashboard.setPlainText("В этой организации пока нет сотрудников.\nСоздайте команду из пресета или добавьте сотрудников.")
        self.professions.setMinimumWidth(280)
        self.organizations.setMinimumWidth(280)
        self.templates.setMinimumWidth(360)
        create_profession = QPushButton("Создать профессию")
        create_organization = QPushButton("Создать организацию")
        create_template = QPushButton("Создать шаблон")
        instantiate = QPushButton("Создать команду из пресета")
        seed = QPushButton("Загрузить демонстрационные шаблоны")
        archive_organization = QPushButton("Архивировать")
        restore_organization = QPushButton("Восстановить")
        delete_organization = QPushButton("Удалить пустую")
        cleanup_legacy = QPushButton("Демо-сотрудники")
        create_profession.clicked.connect(self.create_profession)
        create_organization.clicked.connect(self.create_organization)
        create_template.clicked.connect(self.create_template)
        instantiate.clicked.connect(self.instantiate_template)
        seed.clicked.connect(self.seed_fixtures)
        archive_organization.clicked.connect(lambda: self.change_organization_status("ARCHIVED"))
        restore_organization.clicked.connect(lambda: self.change_organization_status("ACTIVE"))
        delete_organization.clicked.connect(self.delete_selected_organization)
        cleanup_legacy.clicked.connect(self.cleanup_legacy_agents)
        self.template_search.textChanged.connect(self.refresh)
        self.organizations.currentItemChanged.connect(self._show_organization_dashboard)
        actions = QHBoxLayout()
        for button in (create_profession, create_organization, create_template, instantiate, seed, archive_organization, restore_organization, delete_organization, cleanup_legacy):
            actions.addWidget(button)
        columns = QHBoxLayout()
        columns.addLayout(self._column("Профессии", self.professions), 1)
        columns.addLayout(self._column("Организации", self.organizations), 1)
        columns.addLayout(self._column("Шаблоны", self.templates), 1)
        note = QLabel("Профессия, организация и шаблон хранятся отдельно от AI-провайдера. Роли и workflow задаются данными, а не кодом.")
        note.setWordWrap(True)
        dashboard_title = QLabel("МОЯ ОРГАНИЗАЦИЯ")
        dashboard_title.setObjectName("sectionTitle")
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(actions)
        layout.addWidget(self.template_search)
        layout.addLayout(columns, 1)
        layout.addWidget(dashboard_title)
        layout.addWidget(self.organization_dashboard)

    @staticmethod
    def _column(title: str, widget: QListWidget) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(QLabel(title))
        layout.addWidget(widget, 1)
        return layout

    def refresh(self) -> None:
        self.professions.clear()
        self.organizations.clear()
        self.templates.clear()
        if self.service is None:
            return
        for item in self.service.list_professions():
            self.professions.addItem(f"{catalog_label(self.language, item.name)} · {workflow_label(self.language, item.status)}")
        for item in self.service.list_organizations():
            row = QListWidgetItem(f"{item.name} · {workflow_label(self.language, item.status)}")
            row.setData(Qt.UserRole, item.organization_id)
            self.organizations.addItem(row)
        query = self.template_search.text().strip().lower()
        for item in self.service.list_templates():
            searchable = " ".join((item.name, catalog_label(self.language, item.name), item.purpose, item.catalog_category, item.domain_package)).lower()
            if query and query not in searchable:
                continue
            row = QListWidgetItem(f"{catalog_label(self.language, item.name)} · {team_size_label(self.language, item.recommended_team_size)}")
            row.setData(Qt.UserRole, item.template_id)
            self.templates.addItem(row)

    def create_profession(self) -> None:
        if self.service is None:
            return
        name, ok = QInputDialog.getText(self, "Новая профессия", "Название:")
        if not ok or not name.strip():
            return
        description, _ = QInputDialog.getText(self, "Новая профессия", "Описание:")
        try:
            self.service.create_profession(name, description)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Профессия не создана", str(exc))

    def create_organization(self) -> None:
        if self.service is None:
            return
        name, ok = QInputDialog.getText(self, "Новая организация", "Название:")
        if not ok or not name.strip():
            return
        purpose, _ = QInputDialog.getText(self, "Новая организация", "Назначение:")
        try:
            self.service.create_organization(name, purpose)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Организация не создана", str(exc))

    def _selected_organization_id(self) -> str | None:
        item = self.organizations.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def change_organization_status(self, status: str) -> None:
        if self.service is None:
            return
        organization_id = self._selected_organization_id()
        if not organization_id:
            return
        try:
            self.service.set_organization_status(organization_id, status)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Статус не изменён", friendly_error(str(exc), self.language))

    def delete_selected_organization(self) -> None:
        if self.service is None:
            return
        organization_id = self._selected_organization_id()
        if not organization_id:
            return
        reply = QMessageBox.question(self, "Удалить организацию", "Удалить организацию навсегда? Её членство и история чата будут удалены, профили сотрудников останутся.")
        if reply != QMessageBox.Yes:
            return
        try:
            self.service.delete_organization(organization_id)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Организация не удалена", friendly_error(str(exc), self.language))

    def cleanup_legacy_agents(self) -> None:
        management = getattr(self.service, "management_service", None)
        if management is None:
            return
        legacy = management.legacy_seed_agents()
        if not legacy:
            QMessageBox.information(self, "Демо-сотрудники", "Демонстрационные сотрудники не найдены.")
            return
        names = ", ".join(item.display_name for item in legacy)
        answer = QMessageBox.question(
            self,
            "Очистить демонстрационных сотрудников",
            f"Найдены профили: {names}.\n\nДа — архивировать, Нет — отменить. Навсегда удалить можно в разделе «Сотрудники».",
        )
        if answer != QMessageBox.Yes:
            return
        management.cleanup_legacy_seed_agents("ARCHIVE")
        self.refresh()

    def _show_organization_dashboard(self, current, _previous=None) -> None:
        if self.service is None or current is None:
            self.organization_dashboard.setPlainText("В этой организации пока нет сотрудников.\nСоздайте команду из пресета или добавьте сотрудников.")
            return
        organization_id = str(current.data(Qt.UserRole) or "")
        data = self.service.organization_dashboard(organization_id)
        members = data.get("members", [])
        lines = [
            f"Название: {data.get('name', '')}",
            f"Статус: {data.get('status', '')}",
            f"Сотрудники: {data.get('employees', 0)}",
            f"Активные задачи: {data.get('active_tasks', 0)}",
            f"Ожидают проверки: {data.get('pending_review', 0)}",
            "",
            "СОСТАВ",
        ]
        lines.extend(f"- {item.get('position') or 'Специалист'} · {item.get('provider_id') or 'UNAVAILABLE'} · {item.get('provisioning_status') or 'UNASSIGNED'}" for item in members)
        department_names = {str(row["id"]): str(row["name"]) for row in self.service.database.list_organization_departments(organization_id)}
        departments: dict[str, list[str]] = {}
        for item in members:
            department_id = str(item.get("department_id") or "")
            departments.setdefault(department_names.get(department_id, "Команда"), []).append(str(item.get("position") or "Специалист"))
        lines.extend(["", "СТРУКТУРА"])
        for department, positions in departments.items():
            lines.append(f"{department}")
            lines.extend(f"  └─ {position}" for position in positions)
        lines.extend(["", "Следующие действия: открыть чат, назначить AI-движки, настроить workflow и проверить права."])
        self.organization_dashboard.setPlainText("\n".join(lines))

    def create_template(self) -> None:
        if self.service is None:
            return
        name, ok = QInputDialog.getText(self, "Новый шаблон", "Название:")
        if not ok or not name.strip():
            return
        purpose, ok = QInputDialog.getText(self, "Новый шаблон", "Назначение:")
        if not ok:
            return
        roles_text, ok = QInputDialog.getText(self, "Новый шаблон", "Роли через запятую:")
        if not ok:
            return
        roles = [{"role": role.strip(), "position": role.strip()} for role in roles_text.split(",") if role.strip()]
        try:
            self.service.create_template(name, purpose, roles)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Шаблон не создан", str(exc))

    def instantiate_template(self) -> None:
        if self.service is None:
            return
        item = self.templates.currentItem()
        if item is None:
            QMessageBox.information(self, "Шаблон", "Выберите шаблон.")
            return
        try:
            template = next(template for template in self.service.list_templates() if template.template_id == str(item.data(Qt.UserRole)))
            wizard = OrganizationActivationWizard(self.service, template, self.language, self)
            if wizard.exec() != QDialog.Accepted:
                return
            activation = wizard.activation
            summary = f"Команда создана: {activation.organization.name}\nСотрудников: {len(activation.employee_ids)}\nСтатус: {activation.status}"
            if activation.missing_providers:
                summary += "\n\nТребуется AI-движок:\n- " + "\n- ".join(activation.missing_providers)
            QMessageBox.information(self, "Организация готова", summary)
            self.refresh()
            if self.organizations.count():
                self.organizations.setCurrentRow(self.organizations.count() - 1)
        except Exception as exc:
            QMessageBox.warning(self, "Организация не создана", str(exc))

    def seed_fixtures(self) -> None:
        if self.service is not None:
            self.service.seed_demo_fixtures()
            self.refresh()


class OrganizationActivationWizard(QWizard):
    def __init__(self, service: UniversalPlatformService, template, language: str = "ru", parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.template = template
        self.language = language
        self.activation = None
        copy = {
            "ru": {
                "title": "Создать организацию", "step1": "Шаг 1. Название и размер",
                "name_hint": "Например: Команда разработки продукта", "organization_name": "Название организации",
                "team_size": "Размер команды", "preset": "Шаблон", "step2": "Шаг 2. Сотрудники и ИИ-движки",
                "roster_hint": "Сотрудники будут созданы автоматически. Для выполнения задач назначьте подключённый ИИ-движок.",
                "later": "Назначить позже", "create": "Создать нового", "existing": "Использовать существующего",
                "choose_employee": "Выберите сотрудника", "step3": "Шаг 3. Порядок работы и структура",
                "category": "Категория", "size": "Размер", "members": "Состав",
                "workflow": "Порядок работы: результат каждого шага передаётся следующему ответственному.",
                "step4": "Шаг 4. Подтверждение",
                "confirm": "После подтверждения создаются сотрудники, роли, рабочая папка, маршрутизация и порядок работы. Неназначенный ИИ-движок не устанавливается автоматически.",
                "name_missing": "Не указано название", "enter_name": "Введите название организации.",
                "activation_failed": "Активация не завершена",
            },
            "uk": {
                "title": "Створити організацію", "step1": "Крок 1. Назва і розмір",
                "name_hint": "Наприклад: Команда розроблення продукту", "organization_name": "Назва організації",
                "team_size": "Розмір команди", "preset": "Шаблон", "step2": "Крок 2. Співробітники та ШІ-рушії",
                "roster_hint": "Співробітники будуть створені автоматично. Для виконання завдань призначте підключений ШІ-рушій.",
                "later": "Призначити пізніше", "create": "Створити нового", "existing": "Використати наявного",
                "choose_employee": "Оберіть співробітника", "step3": "Крок 3. Порядок роботи і структура",
                "category": "Категорія", "size": "Розмір", "members": "Склад",
                "workflow": "Порядок роботи: результат кожного кроку передається наступному відповідальному.",
                "step4": "Крок 4. Підтвердження",
                "confirm": "Після підтвердження створюються співробітники, ролі, робоча папка, маршрутизація і порядок роботи. Непризначений ШІ-рушій не встановлюється автоматично.",
                "name_missing": "Не вказано назву", "enter_name": "Введіть назву організації.",
                "activation_failed": "Активацію не завершено",
            },
            "en": {
                "title": "Create organization", "step1": "Step 1. Name and size",
                "name_hint": "For example: Product development team", "organization_name": "Organization name",
                "team_size": "Team size", "preset": "Template", "step2": "Step 2. Employees and AI providers",
                "roster_hint": "Employees will be created automatically. Assign a connected AI provider to perform tasks.",
                "later": "Assign later", "create": "Create new", "existing": "Use existing",
                "choose_employee": "Choose an employee", "step3": "Step 3. Workflow and structure",
                "category": "Category", "size": "Size", "members": "Team",
                "workflow": "Workflow: the result of each step is handed to the next responsible employee.",
                "step4": "Step 4. Confirmation",
                "confirm": "Confirmation creates employees, roles, workspace, routing and workflow. An unassigned AI provider is not installed automatically.",
                "name_missing": "Name is missing", "enter_name": "Enter an organization name.",
                "activation_failed": "Activation did not finish",
            },
        }.get(language, {})
        if not copy:
            copy = {
                "title": "Create organization", "step1": "Step 1. Name and size", "name_hint": "Product team",
                "organization_name": "Organization name", "team_size": "Team size", "preset": "Template",
                "step2": "Step 2. Employees and AI providers", "roster_hint": "Assign connected AI providers.",
                "later": "Assign later", "create": "Create new", "existing": "Use existing", "choose_employee": "Choose an employee",
                "step3": "Step 3. Workflow and structure", "category": "Category", "size": "Size", "members": "Team",
                "workflow": "Each result is handed to the next responsible employee.", "step4": "Step 4. Confirmation",
                "confirm": "Create the organization and its employees.", "name_missing": "Name is missing",
                "enter_name": "Enter an organization name.", "activation_failed": "Activation did not finish",
            }
        self._copy = copy
        self.setWindowTitle(copy["title"])
        self.setMinimumSize(720, 560)

        identity = QWizardPage()
        identity.setTitle(copy["step1"])
        self.organization_name = QLineEdit()
        self.organization_name.setPlaceholderText(copy["name_hint"])
        self.team_size = QComboBox()
        for value in ("MINI", "STANDARD", "EXTENDED"):
            self.team_size.addItem(team_size_label(language, value), value)
        standard_index = self.team_size.findData("STANDARD")
        self.team_size.setCurrentIndex(standard_index if standard_index >= 0 else 0)
        form = QFormLayout(identity)
        form.addRow(copy["organization_name"], self.organization_name)
        form.addRow(copy["team_size"], self.team_size)
        form.addRow(
            copy["preset"],
            QLabel(f"{catalog_label(language, template.name)}\n{catalog_purpose(language, template.name, template.purpose)}"),
        )
        self.addPage(identity)

        roster = QWizardPage()
        roster.setTitle(copy["step2"])
        self.provider_boxes: dict[str, QComboBox] = {}
        self.mode_boxes: dict[str, QComboBox] = {}
        self.existing_boxes: dict[str, QComboBox] = {}
        roster_layout = QVBoxLayout(roster)
        roster_layout.addWidget(QLabel(copy["roster_hint"]))
        for role in template.roles:
            position = str(role.get("position") or role.get("role") or "Специалист")
            row = QHBoxLayout()
            row.addWidget(QLabel(catalog_label(language, position)), 2)
            provider = QComboBox()
            for value, label in (("UNAVAILABLE", copy["later"]), ("CODEX_CLI", "Codex CLI"), ("GEMINI_CLI", "Gemini CLI"), ("CLAUDE_CLI", "Claude CLI")):
                provider.addItem(label, value)
            self.provider_boxes[position] = provider
            mode = QComboBox()
            mode.addItem(copy["create"], "CREATE")
            mode.addItem(copy["existing"], "EXISTING")
            self.mode_boxes[position] = mode
            existing = QComboBox()
            existing.addItem(copy["choose_employee"], "")
            for employee in service.database.list_agent_profiles():
                existing.addItem(str(employee["display_name"]), str(employee["agent_id"]))
            self.existing_boxes[position] = existing
            existing.setEnabled(False)
            mode.currentIndexChanged.connect(lambda _index, key=position: self.existing_boxes[key].setEnabled(self.mode_boxes[key].currentData() == "EXISTING"))
            row.addWidget(provider, 1)
            row.addWidget(mode, 1)
            row.addWidget(existing, 1)
            roster_layout.addLayout(row)
        roster_layout.addStretch(1)
        self.addPage(roster)

        workflow = QWizardPage()
        workflow.setTitle(copy["step3"])
        workflow_layout = QVBoxLayout(workflow)
        structure = [f"{copy['preset']}: {catalog_label(language, template.name)}", f"{copy['category']}: {catalog_label(language, template.catalog_category)}", f"{copy['size']}: {team_size_label(language, template.recommended_team_size)}", "", f"{copy['members']}:"]
        structure.extend(f"  {index}. {catalog_label(language, str(role.get('position') or role.get('role') or 'Специалист'))}" for index, role in enumerate(template.roles, start=1))
        structure.extend(["", copy["workflow"]])
        workflow_layout.addWidget(QLabel("\n".join(structure)))
        workflow_layout.addStretch(1)
        self.addPage(workflow)

        confirmation = QWizardPage()
        confirmation.setTitle(copy["step4"])
        confirmation_layout = QVBoxLayout(confirmation)
        confirmation_layout.addWidget(QLabel(copy["confirm"]))
        confirmation_layout.addStretch(1)
        self.addPage(confirmation)

    def accept(self) -> None:
        if not self.organization_name.text().strip():
            QMessageBox.warning(self, self._copy["name_missing"], self._copy["enter_name"])
            return
        assignments = {position: str(box.currentData()) for position, box in self.provider_boxes.items()}
        existing = {
            position: str(box.currentData())
            for position, box in self.existing_boxes.items()
            if self.mode_boxes[position].currentData() == "EXISTING" and box.currentData()
        }
        try:
            self.activation = self.service.activate_template(
                self.template.template_id,
                self.organization_name.text().strip(),
                team_size=str(self.team_size.currentData()),
                provider_assignments=assignments,
                use_existing_agents=existing,
            )
        except Exception as exc:
            QMessageBox.critical(self, self._copy["activation_failed"], str(exc))
            return
        super().accept()


class OverviewTab(QWidget):
    def __init__(self, service: ManagementService, provider_health_service: ProviderHealthService, console: DirectorConsoleDialog) -> None:
        super().__init__()
        self.service = service
        self.provider_health_service = provider_health_service
        self.console = console
        self.language = console.language
        self.grid = QGridLayout()
        self.recent = QTextEdit()
        self.recent.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addLayout(self.grid)
        layout.addWidget(QLabel("Последние действия"))
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
            ("Активные сотрудники", counts.get("ACTIVE", 0)),
            ("Приостановлены", counts.get("SUSPENDED", 0)),
            ("Отключены", counts.get("DISABLED", 0)),
            ("Архив", counts.get("ARCHIVED", 0)),
            ("Настроенные роли", len(self.service.list_roles())),
            (tr(self.language, "providers_available"), available),
            (tr(self.language, "providers_unavailable"), unavailable),
            ("Рискованные конфигурации", len([item for item in employees if item.warnings])),
            ("База данных", "OK"),
            (tr(self.language, "management_repository"), "OK"),
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
        self.recent.setPlainText("\n".join(lines) if lines else "Действий пока нет.")


class LearningEvidenceTab(QWidget):
    def __init__(
        self,
        service: LearningEvidenceService,
        language: str = "ru",
        parent=None,
        manager: LearningManagerService | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.manager = manager
        self.language = language
        copy = {
            "ru": {
                "experience": "Подтверждённый опыт", "queue": "Очередь обучения",
                "employee": "Сотрудник", "result": "Результат", "skills": "Навыки",
                "evidence": "Доказательства", "outcome": "Итог", "date": "Дата",
                "competence": "Компетенция", "reason": "Причина", "status": "Статус",
                "practice": "Практическая проверка", "approve": "Одобрить", "start": "Начать",
                "reject": "Отклонить", "details": "Основание и данные проверки",
            },
            "uk": {
                "experience": "Підтверджений досвід", "queue": "Черга навчання",
                "employee": "Співробітник", "result": "Результат", "skills": "Навички",
                "evidence": "Докази", "outcome": "Підсумок", "date": "Дата",
                "competence": "Компетенція", "reason": "Причина", "status": "Статус",
                "practice": "Практична перевірка", "approve": "Схвалити", "start": "Почати",
                "reject": "Відхилити", "details": "Підстава та дані перевірки",
            },
            "en": {
                "experience": "Verified experience", "queue": "Learning queue",
                "employee": "Employee", "result": "Result", "skills": "Skills",
                "evidence": "Evidence", "outcome": "Outcome", "date": "Date",
                "competence": "Competence", "reason": "Reason", "status": "Status",
                "practice": "Practice check", "approve": "Approve", "start": "Start",
                "reject": "Reject", "details": "Basis and verification data",
            },
        }.get(language, {})
        self.copy = copy or {
            "experience": "Verified experience", "queue": "Learning queue", "employee": "Employee",
            "result": "Result", "skills": "Skills", "evidence": "Evidence", "outcome": "Outcome",
            "date": "Date", "competence": "Competence", "reason": "Reason", "status": "Status",
            "practice": "Practice check", "approve": "Approve", "start": "Start", "reject": "Reject",
            "details": "Basis and verification data",
        }
        copy = self.copy
        self.experience_table = QTableWidget(0, 6)
        self.experience_table.setHorizontalHeaderLabels(
            [copy["employee"], copy["result"], copy["skills"], copy["evidence"], copy["outcome"], copy["date"]]
        )
        self.experience_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.experience_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.experience_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table = QTableWidget(0, 6)
        self.queue_table.setHorizontalHeaderLabels(
            [copy["employee"], copy["competence"], copy["reason"], copy["status"], copy["practice"], copy["date"]]
        )
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(110)
        self.experience_table.itemSelectionChanged.connect(self._show_experience_detail)
        self.queue_table.itemSelectionChanged.connect(self._show_queue_detail)
        buttons = QHBoxLayout()
        for label, status in ((copy["approve"], "APPROVED"), (copy["start"], "IN_PROGRESS"), (copy["reject"], "REJECTED")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, value=status: self._set_queue_status(value))
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(copy["experience"]))
        layout.addWidget(self.experience_table, 1)
        layout.addWidget(QLabel(copy["queue"]))
        layout.addWidget(self.queue_table, 1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel(copy["details"]))
        layout.addWidget(self.detail)

    def refresh(self) -> None:
        experience = self.service.list_experience()
        self.experience_table.setRowCount(len(experience))
        for row_index, record in enumerate(experience):
            evidence_count = sum(len(value) for value in record.evidence.values() if isinstance(value, list))
            values = [
                record.employee_name,
                record.summary,
                ", ".join(record.skills_used),
                str(evidence_count),
                workflow_label(self.language, record.outcome),
                record.created_at,
            ]
            detail = json.dumps(
                {
                    "summary": record.summary,
                    "skills_used": record.skills_used,
                    "errors_found": record.errors_found,
                    "corrections": record.corrections,
                    "lessons_learned": record.lessons_learned,
                    "evidence": record.evidence,
                },
                ensure_ascii=False,
                indent=2,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, detail)
                self.experience_table.setItem(row_index, column, item)
        queue = self.service.list_learning_queue()
        self.queue_table.setRowCount(len(queue))
        for row_index, item_data in enumerate(queue):
            values = [
                item_data.employee_name,
                item_data.competence,
                item_data.reason,
                workflow_label(self.language, item_data.status),
                item_data.practice_task,
                item_data.updated_at,
            ]
            detail = json.dumps(
                {
                    "skill_id": item_data.skill_id,
                    "coordinator_agent_id": item_data.coordinator_agent_id,
                    "qualification_criteria": item_data.qualification_criteria,
                    "practice_run_id": item_data.practice_run_id,
                    "review_run_id": item_data.review_run_id,
                    "evidence": item_data.evidence,
                },
                ensure_ascii=False,
                indent=2,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, item_data.item_id)
                item.setData(Qt.UserRole + 1, detail)
                self.queue_table.setItem(row_index, column, item)

    def _show_experience_detail(self) -> None:
        items = self.experience_table.selectedItems()
        if items:
            self.detail.setPlainText(str(items[0].data(Qt.UserRole) or ""))

    def _show_queue_detail(self) -> None:
        items = self.queue_table.selectedItems()
        if items:
            self.detail.setPlainText(str(items[0].data(Qt.UserRole + 1) or ""))

    def _set_queue_status(self, status: str) -> None:
        items = self.queue_table.selectedItems()
        if not items:
            return
        item_id = str(items[0].data(Qt.UserRole) or "")
        try:
            evidence = json.loads(str(items[0].data(Qt.UserRole + 1) or "{}"))
        except json.JSONDecodeError:
            evidence = {}
        if status == "IN_PROGRESS" and self.manager is not None:
            self.manager.prepare_learning_item(item_id)
        else:
            self.service.update_learning_status(item_id, status, evidence)
        self.refresh()


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

        self.table = QTableWidget(0, 8)
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
        delete = QPushButton(tr(language, "delete_permanently"))
        add.clicked.connect(self.add_employee)
        open_button.clicked.connect(self._show_selected_detail)
        edit.clicked.connect(self.edit_employee)
        suspend.clicked.connect(lambda: self.lifecycle_action("SUSPENDED"))
        reactivate.clicked.connect(lambda: self.lifecycle_action("ACTIVE"))
        archive.clicked.connect(lambda: self.lifecycle_action("ARCHIVED"))
        delete.clicked.connect(self.delete_selected_employee)

        filters = QHBoxLayout()
        filters.addWidget(self.status_filter)
        filters.addWidget(self.role_filter)
        filters.addWidget(self.provider_filter)
        filters.addWidget(self.warning_filter)
        filters.addStretch(1)

        actions = QHBoxLayout()
        for button in (add, open_button, edit, suspend, reactivate, archive, delete):
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
                f"{len(employee.effective_permissions)} прав",
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
            self.detail.setPlainText("Профиль не найден.")
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
        reason = "Действие владельца организации"
        try:
            if target_state == "SUSPENDED":
                    self.service.suspend_agent(agent_id, OWNER_ROLE, reason)
            elif target_state == "ACTIVE":
                employee = self.service.get_employee(agent_id)
                if employee and employee.lifecycle_state == "DRAFT":
                    self.service.activate_agent(agent_id, OWNER_ROLE, reason)
                else:
                    self.service.reactivate_agent(agent_id, OWNER_ROLE, reason)
            elif target_state == "ARCHIVED":
                reply = QMessageBox.question(self, "Архивировать", "История сохранится. Архивировать сотрудника?")
                if reply != QMessageBox.Yes:
                    return
                self.service.archive_agent(agent_id, OWNER_ROLE, reason)
        except Exception as exc:
            QMessageBox.warning(self, tr(self.language, "rejected"), friendly_error(str(exc), self.language))
            return
        self.console.refresh_all()

    def delete_selected_employee(self) -> None:
        agent_id = self.selected_agent_id()
        if not agent_id:
            return
        reply = QMessageBox.question(
            self,
            "Удалить сотрудника навсегда",
            "Профиль, настройки, доступы и персональная память будут удалены.\n"
            "Общая история, задачи и артефакты останутся с пометкой удалённого автора.\n\n"
            "Действие необратимо. Продолжить?",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.service.delete_agent(agent_id, OWNER_ROLE, confirmed=True)
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
        language: str = "ru",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.package_service = package_service
        self.management_service = management_service
        self.language = language
        self.package_table = QTableWidget(0, 6)
        self.package_table.setHorizontalHeaderLabels(["Навык", "Статус", "Версия", "Назначено", "Назначение", "Обновлен"])
        self.package_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.package_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.package_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.package_table.itemSelectionChanged.connect(self._show_selected_package_detail)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "Сотрудник",
                "Навык",
                "Уровень",
                "Подтверждения",
                "Задач",
                "Ревью",
                "Квалификация",
                "Последний результат",
                "Следующий шаг",
                "Достоверность",
                "Шкала",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        create_button = QPushButton("Создать пакет навыка")
        create_button.clicked.connect(self._create_package)
        activate_button = QPushButton("Активировать")
        activate_button.clicked.connect(lambda: self._set_selected_package_status("ACTIVE"))
        suspend_button = QPushButton("Приостановить")
        suspend_button.clicked.connect(lambda: self._set_selected_package_status("SUSPENDED"))
        assign_button = QPushButton("Назначить сотруднику")
        assign_button.clicked.connect(self._assign_selected_package)
        evidence_button = QPushButton("Показать доказательства")
        evidence_button.clicked.connect(self._show_selected_detail)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Пакет навыка управляется владельцем. Назначение сотруднику не повышает уровень: прогресс растет только от задач, артефактов и ревью."))
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
        layout.addWidget(QLabel("Прогресс навыков по подтвержденным результатам"))
        layout.addWidget(self.table, 2)
        layout.addWidget(QLabel("Доказательства и основание расчета"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        self._refresh_packages()
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Расчет навыков недоступен.")
            return
        rows = self.service.list_progress()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.employee_name,
                row.skill_title,
                workflow_label(self.language, row.status),
                row.evidence_summary,
                str(row.tasks_completed),
                str(row.reviews_passed),
                row.qualification,
                row.last_demonstrated or "нет",
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
                            f"Сотрудник: {row.employee_name} ({row.agent_id})",
                            f"Навык: {row.skill_title}",
                            f"Уровень: {workflow_label(self.language, row.status)}",
                            f"Подтверждения: {row.evidence_summary}",
                            f"Следующий шаг: {row.next_required_step}",
                            f"Достоверность: {row.confidence}",
                            f"Процент: {row.percent}%",
                            f"Обновлен: {row.updated_at or 'нет'}",
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
            self.detail.setPlainText("Навыков пока нет.")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.detail.setPlainText(str(items[0].data(Qt.UserRole) or "Нет данных."))

    def _refresh_packages(self) -> None:
        if self.package_service is None:
            self.package_table.setRowCount(0)
            return
        packages = self.package_service.list_packages()
        assignments = self.package_service.list_assignments()
        by_skill: dict[str, list[str]] = {}
        for assignment in assignments:
            by_skill.setdefault(assignment.skill_id, []).append(
                f"{assignment.agent_id}: {workflow_label(self.language, assignment.state)}"
            )
        self.package_table.setRowCount(len(packages))
        for row_index, package in enumerate(packages):
            assigned = by_skill.get(package.skill_id, [])
            values = [
                package.name,
                workflow_label(self.language, package.status),
                package.version,
                str(len(assigned)),
                "; ".join(assigned) or "нет",
                package.updated_at or "нет",
            ]
            detail = "\n".join(
                [
                    f"ID: {package.skill_id}",
                    f"Название: {package.name}",
                    f"Статус: {workflow_label(self.language, package.status)}",
                    f"Версия: {package.version}",
                    f"Назначения: {'; '.join(assigned) or 'нет'}",
                    f"Назначаемые роли: {', '.join(package.supported_roles) or 'не указаны'}",
                    f"Цель: {package.purpose or 'не указана'}",
                    f"Входы: {package.expected_inputs or 'не указаны'}",
                    f"Выходы: {package.expected_outputs or 'не указаны'}",
                    f"Запрещено: {package.prohibited_actions or 'не указано'}",
                    "Чек-лист:",
                    *[f"- {item}" for item in package.validation_checklist],
                    "Квалификационные задачи:",
                    *[f"- {item}" for item in package.qualification_tasks],
                    "",
                    "Инструкции:",
                    package.instructions or "не указаны",
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
        self.detail.setPlainText(str(items[0].data(Qt.UserRole + 1) or "Нет данных."))

    def _selected_skill_id(self) -> str | None:
        items = self.package_table.selectedItems()
        if not items:
            QMessageBox.information(self, "Навык", "Выберите пакет навыка.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _create_package(self) -> None:
        if self.package_service is None:
            QMessageBox.warning(self, "Навыки", "Управление пакетами навыков недоступно.")
            return
        dialog = SkillPackageDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.package_service.create_package(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "Навык не создан", str(exc))
            return
        self.refresh()

    def _set_selected_package_status(self, status: str) -> None:
        if self.package_service is None:
            return
        skill_id = self._selected_skill_id()
        if not skill_id:
            return
        try:
            self.package_service.update_status(skill_id, status, actor=OWNER_ROLE, reason="изменено через Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "Статус не изменен", str(exc))
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
            QMessageBox.information(self, "Назначение", "Нет сотрудников для назначения.")
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
                reason="назначено через Director Console",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Навык не назначен", str(exc))
            return
        self.refresh()


class SkillPackageDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self)
        self.setWindowTitle("Создать пакет навыка")
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
        layout.addRow("Название", self.name)
        layout.addRow("Цель", self.purpose)
        layout.addRow("Роли через запятую", self.roles)
        layout.addRow("Инструкции", self.instructions)
        layout.addRow("Ожидаемые входы", self.expected_inputs)
        layout.addRow("Ожидаемые выходы", self.expected_outputs)
        layout.addRow("Запрещенные действия", self.prohibited_actions)
        layout.addRow("Чек-лист, по строке", self.validation)
        layout.addRow("Квалификационные задачи", self.qualification)
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
        apply_team_dialog_chrome(self)
        self.setWindowTitle("Назначить навык")
        self.employee = QComboBox()
        for item in employees:
            self.employee.addItem(f"{item.display_name} ({item.agent_id})", item.agent_id)
        self.skill_state = QComboBox()
        for state in ("ASSIGNED", "STUDYING", "PRACTICED", "DEMONSTRATED", "REVIEWED", "REQUIRES_RETRAINING"):
            self.skill_state.addItem(workflow_label(getattr(parent, "language", "ru"), state), state)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("Сотрудник", self.employee)
        layout.addRow("Состояние", self.skill_state)
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

        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Добавить карточку")
        create.clicked.connect(self._create_card)
        activate = QPushButton("Активировать")
        activate.clicked.connect(lambda: self._set_selected_status("ACTIVE"))
        review = QPushButton("На ревью")
        review.clicked.connect(lambda: self._set_selected_status("NEEDS_REVIEW"))
        reject = QPushButton("Отклонить")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Карточки знаний управляются владельцем. ACTIVE попадают в контекст, а применение считается отдельно: SUPPLIED / APPLIED / IGNORED / MISAPPLIED."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, activate, review, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Карточка и аудит"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Сервис знаний недоступен.")
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
                card.source_title or card.source_uri or "не указан",
                ", ".join(card.role_ids) or "все",
                ", ".join(card.tags) or "нет",
                card.version,
                card.updated_at or "нет",
                str(counts.supplied if counts else 0),
                str(counts.applied if counts else 0),
                str(counts.ignored if counts else 0),
                str(counts.misapplied if counts else 0),
            ]
            detail = "\n".join(
                [
                    f"ID: {card.knowledge_id}",
                    f"Название: {card.title}",
                    f"Статус: {card.status}",
                    f"Надежность источника: {card.source_authority}",
                    f"Тип источника: {card.source_type}",
                    f"Источник: {card.source_title or 'не указан'}",
                    f"Ссылка/путь: {card.source_uri or 'не указан'}",
                    f"Хэш: {card.source_hash or 'не указан'}",
                    f"Роли: {', '.join(card.role_ids) or 'все'}",
                    f"Теги: {', '.join(card.tags) or 'нет'}",
                    f"Версия: {card.version}",
                    f"Заметки ревью: {card.review_notes or 'нет'}",
                    f"Использование: SUPPLIED={counts.supplied if counts else 0}; APPLIED={counts.applied if counts else 0}; IGNORED={counts.ignored if counts else 0}; MISAPPLIED={counts.misapplied if counts else 0}",
                    "",
                    "Кратко:",
                    card.summary or "не заполнено",
                    "",
                    "Содержание:",
                    card.content or "не заполнено",
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
            self.detail.setPlainText("Карточек знаний пока нет.")

    def _selected_knowledge_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Знания", "Выберите карточку.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "Нет данных.")
        knowledge_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and knowledge_id:
            events = self.service.list_events(knowledge_id)
            if events:
                detail += "\n\nАудит:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
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
            QMessageBox.warning(self, "Знание не создано", str(exc))
            return
        self.refresh()

    def _set_selected_status(self, status: str) -> None:
        if self.service is None:
            return
        knowledge_id = self._selected_knowledge_id()
        if not knowledge_id:
            return
        try:
            self.service.update_status(knowledge_id, status, actor=OWNER_ROLE, reason="изменено через Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "Статус не изменен", str(exc))
            return
        self.refresh()


class KnowledgeCardDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self)
        self.setWindowTitle("Добавить карточку знаний")
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
        layout.addRow("Название", self.title)
        layout.addRow("Кратко", self.summary)
        layout.addRow("Содержание", self.content)
        layout.addRow("Тип источника", self.source_type)
        layout.addRow("Название источника", self.source_title)
        layout.addRow("Ссылка/путь", self.source_uri)
        layout.addRow("Надежность источника", self.source_authority)
        layout.addRow("Роли через запятую", self.roles)
        layout.addRow("Теги через запятую", self.tags)
        layout.addRow("Заметки ревью", self.review_notes)
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

        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Добавить стандарт")
        create.clicked.connect(self._create_card)
        activate = QPushButton("Активировать")
        activate.clicked.connect(lambda: self._set_selected_status("ACTIVE"))
        suspend = QPushButton("Приостановить")
        suspend.clicked.connect(lambda: self._set_selected_status("SUSPENDED"))
        reject = QPushButton("Отклонить")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Стандарты управляются владельцем. ACTIVE попадают в контекст, а применение считается отдельно: SUPPLIED / APPLIED / IGNORED / MISAPPLIED."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, activate, suspend, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Требование и аудит"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Сервис стандартов недоступен.")
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
                card.source_title or card.source_uri or "не указан",
                ", ".join(card.role_ids) or "все",
                ", ".join(card.tags) or "нет",
                card.version,
                card.updated_at or "нет",
                str(counts.supplied if counts else 0),
                str(counts.applied if counts else 0),
                str(counts.ignored if counts else 0),
                str(counts.misapplied if counts else 0),
            ]
            detail = "\n".join(
                [
                    f"ID: {card.standard_id}",
                    f"Код: {card.code}",
                    f"Название: {card.title}",
                    f"Статус: {card.status}",
                    f"Обязательность: {card.mandatory_level}",
                    f"Authority: {card.authority}",
                    f"Источник: {card.source_title or 'не указан'}",
                    f"Ссылка/путь: {card.source_uri or 'не указан'}",
                    f"Хэш: {card.source_hash or 'не указан'}",
                    f"Роли: {', '.join(card.role_ids) or 'все'}",
                    f"Теги: {', '.join(card.tags) or 'нет'}",
                    f"Версия: {card.version}",
                    f"Область применения: {card.scope or 'не указана'}",
                    f"Заметки ревью: {card.review_notes or 'нет'}",
                    f"Использование: SUPPLIED={counts.supplied if counts else 0}; APPLIED={counts.applied if counts else 0}; IGNORED={counts.ignored if counts else 0}; MISAPPLIED={counts.misapplied if counts else 0}",
                    "",
                    "Требование:",
                    card.requirement or "не заполнено",
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
            self.detail.setPlainText("Стандартов пока нет.")

    def _selected_standard_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Стандарты", "Выберите стандарт.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "Нет данных.")
        standard_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and standard_id:
            events = self.service.list_events(standard_id)
            if events:
                detail += "\n\nАудит:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
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
            QMessageBox.warning(self, "Стандарт не создан", str(exc))
            return
        self.refresh()

    def _set_selected_status(self, status: str) -> None:
        if self.service is None:
            return
        standard_id = self._selected_standard_id()
        if not standard_id:
            return
        try:
            self.service.update_status(standard_id, status, actor=OWNER_ROLE, reason="изменено через Director Console")
        except Exception as exc:
            QMessageBox.warning(self, "Статус не изменен", str(exc))
            return
        self.refresh()


class StandardCardDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self)
        self.setWindowTitle("Добавить стандарт")
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
        layout.addRow("Код", self.code)
        layout.addRow("Название", self.title)
        layout.addRow("Требование", self.requirement)
        layout.addRow("Область применения", self.scope)
        layout.addRow("Источник", self.source_title)
        layout.addRow("Ссылка/путь", self.source_uri)
        layout.addRow("Authority", self.authority)
        layout.addRow("Обязательность", self.mandatory)
        layout.addRow("Роли через запятую", self.roles)
        layout.addRow("Теги через запятую", self.tags)
        layout.addRow("Заметки ревью", self.review_notes)
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
        self.table.setHorizontalHeaderLabels(["Путь", "Статус", "Проверка", "QA", "Задача", "Роль", "Run", "Тип", "Размер", "Изменен"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        open_file = QPushButton("Открыть файл")
        open_file.clicked.connect(self._open_selected_file)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Артефакты показывают реальные следы работы: найденные файлы, отсутствующие заявления и хэши подтвержденных файлов."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        buttons.addWidget(refresh)
        buttons.addWidget(open_file)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Детали артефакта"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Сервис артефактов недоступен.")
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
                artifact.task_id or "нет",
                artifact.authoring_role or "нет",
                artifact.created_by_run_id or "нет",
                artifact.artifact_type or "file",
                str(artifact.size) if artifact.size is not None else "нет",
                artifact.last_modified_time or "нет",
            ]
            detail = "\n".join(
                [
                    f"ID: {artifact.artifact_id}",
                    f"Путь: {artifact.relative_path}",
                    f"Задача: {artifact.task_id or 'нет'}",
                    f"Проект: {artifact.project_id or 'нет'}",
                    f"Статус: {artifact.status}",
                    f"Проверка: {artifact.validation_status}",
                    f"Роль автора: {artifact.authoring_role or 'нет'}",
                    f"Run: {artifact.created_by_run_id or 'нет'}",
                    f"Тип: {artifact.artifact_type or 'file'}",
                    f"Media type: {artifact.media_type or 'нет'}",
                    f"Размер: {artifact.size if artifact.size is not None else 'нет'}",
                    f"SHA-256: {artifact.sha256 or 'нет'}",
                    f"Revision: {artifact.current_revision or 'нет'}",
                    f"Удален: {'да' if artifact.deleted else 'нет'}",
                    f"Изменен: {artifact.last_modified_time or 'нет'}",
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
                        or ["РЅРµС‚"]
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
            ["Задача", "Серьезность", "Статус", "Уверенность", "Стандарт", "Артефакт", "Локация", "Описание", "Действие", "Обновлено"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        create = QPushButton("Добавить finding")
        create.clicked.connect(self._create_finding)
        rework = QPushButton("В доработку")
        rework.clicked.connect(lambda: self._set_selected_status("IN_REWORK"))
        recheck = QPushButton("На перепроверку")
        recheck.clicked.connect(lambda: self._set_selected_status("READY_FOR_RECHECK"))
        resolved = QPushButton("Закрыть")
        resolved.clicked.connect(lambda: self._set_selected_status("RESOLVED"))
        accepted = QPushButton("Принять риск")
        accepted.clicked.connect(lambda: self._set_selected_status("ACCEPTED_RISK"))
        reject = QPushButton("Отклонить")
        reject.clicked.connect(lambda: self._set_selected_status("REJECTED"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Замечания ОТК фиксируют реальные проблемы. Критические открытые замечания блокируют завершение задачи."))
        layout.addWidget(self.table, 2)
        buttons = QHBoxLayout()
        for button in (refresh, create, rework, recheck, resolved, accepted, reject):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Finding и аудит"))
        layout.addWidget(self.detail, 1)

    def refresh(self) -> None:
        if self.service is None:
            self.table.setRowCount(0)
            self.detail.setPlainText("Сервис findings недоступен.")
            return
        findings = self.service.list_findings()
        self.table.setRowCount(len(findings))
        for row_index, finding in enumerate(findings):
            values = [
                finding.task_id,
                finding.severity,
                finding.status,
                finding.confidence,
                finding.standard_id or "нет",
                finding.affected_artifact or "нет",
                finding.location or "нет",
                finding.description,
                finding.required_action or "не указано",
                finding.updated_at or "нет",
            ]
            detail = "\n".join(
                [
                    f"ID: {finding.finding_id}",
                    f"Задача: {finding.task_id}",
                    f"Тип: {finding.finding_type or 'QA_FINDING'}",
                    f"Серьезность: {finding.severity}",
                    f"Статус: {finding.status}",
                    f"Уверенность: {finding.confidence}",
                    f"Стандарт: {finding.standard_id or 'нет'}",
                    f"Артефакт: {finding.affected_artifact or 'нет'}",
                    f"Локация: {finding.location or 'нет'}",
                    f"Repeat key: {finding.repeat_key or 'нет'}",
                    f"Независимая перепроверка: {finding.independent_recheck_status or 'нет'}",
                    "",
                    "Описание:",
                    finding.description,
                    "",
                    "Влияние:",
                    finding.impact or "не указано",
                    "",
                    "Требуемое действие:",
                    finding.required_action or "не указано",
                    "",
                    "Подтверждение:",
                    finding.evidence or "{}",
                    "",
                    "Решение:",
                    finding.resolution or "нет",
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
            self.detail.setPlainText("Замечаний пока нет.")

    def _selected_finding_id(self) -> str | None:
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Замечания ОТК", "Выберите замечание.")
            return None
        return str(items[0].data(Qt.UserRole) or "")

    def _show_selected_detail(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        detail = str(items[0].data(Qt.UserRole + 1) or "Нет данных.")
        finding_id = str(items[0].data(Qt.UserRole) or "")
        if self.service is not None and finding_id:
            events = self.service.list_events(finding_id)
            if events:
                detail += "\n\nАудит:\n" + "\n".join(f"- {event.created_at}: {event.event_type}; {event.detail}" for event in events[:12])
        self.detail.setPlainText(detail)

    def _create_finding(self) -> None:
        if self.service is None:
            return
        tasks = self.service.database.list_tasks()
        if not tasks:
            QMessageBox.information(self, "Замечания ОТК", "Сначала нужна хотя бы одна задача.")
            return
        dialog = FindingDialog(tasks, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_finding(**dialog.values(), actor=OWNER_ROLE)
        except Exception as exc:
            QMessageBox.warning(self, "Finding не создан", str(exc))
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
            resolution, ok = QInputDialog.getText(self, "Решение", "Кратко укажите основание:")
            if not ok:
                return
        try:
            self.service.update_status(finding_id, status, actor=OWNER_ROLE, resolution=resolution)
        except Exception as exc:
            QMessageBox.warning(self, "Статус не изменен", str(exc))
            return
        self.refresh()


class FindingDialog(QDialog):
    def __init__(self, tasks, parent=None) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self)
        self.setWindowTitle("Добавить finding")
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
        layout.addRow("Задача", self.task)
        layout.addRow("Серьезность", self.severity)
        layout.addRow("Уверенность", self.confidence)
        layout.addRow("Идентификатор стандарта", self.standard_id)
        layout.addRow("Артефакт", self.artifact)
        layout.addRow("Локация", self.location)
        layout.addRow("Описание", self.description)
        layout.addRow("Влияние", self.impact)
        layout.addRow("Требуемое действие", self.required_action)
        layout.addRow("Подтверждение", self.evidence)
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


class ProviderCatalogDialog(QDialog):
    def __init__(self, profiles, language: str, parent=None) -> None:
        super().__init__(parent)
        apply_team_dialog_chrome(self, minimum_width=620)
        self.profiles = list(profiles)
        self.language = language
        self.setWindowTitle({"ru": "Добавить ИИ", "uk": "Додати ШІ", "en": "Add AI"}.get(language, "Добавить ИИ"))
        self.setMinimumWidth(620)
        self.provider = QComboBox()
        for profile in self.profiles:
            self.provider.addItem(f"{profile.display_name} · {profile.integration_type}", profile.provider_id)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.provider.currentIndexChanged.connect(self.refresh_detail)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel({"ru": "Выберите подключение из проверенного каталога. Готовность указана без преувеличений.", "uk": "Оберіть підключення з перевіреного каталогу. Готовність указано без перебільшень.", "en": "Choose a connection from the verified catalog. Readiness is stated conservatively."}.get(language, "")))
        layout.addWidget(self.provider)
        layout.addWidget(self.detail)
        layout.addStretch(1)
        layout.addWidget(buttons)
        self.refresh_detail()

    def selected_provider_id(self) -> str:
        return str(self.provider.currentData() or "")

    def refresh_detail(self) -> None:
        provider_id = self.selected_provider_id()
        profile = next((item for item in self.profiles if item.provider_id == provider_id), None)
        if profile is None:
            self.detail.clear()
            return
        labels = {
            "ru": ("Тип подключения", "Поддержка", "Платформы", "Официальный источник", "После выбора используйте доступные действия в карточке подключения."),
            "uk": ("Тип підключення", "Підтримка", "Платформи", "Офіційне джерело", "Після вибору скористайтеся доступними діями в картці підключення."),
            "en": ("Connection type", "Support", "Platforms", "Official source", "After selecting, use the available actions in the connection card."),
        }
        connection, support, platforms, source, hint = labels.get(self.language, labels["ru"])
        states = {
            "ru": {"CLI": "Командная строка", "API": "API", "LOCAL_RUNTIME": "Локальная модель", "GATEWAY": "Шлюз", "SUPPORTED": "Поддерживается", "EXPERIMENTAL": "Экспериментально", "CATALOG_ONLY": "Только в каталоге"},
            "uk": {"CLI": "Командний рядок", "API": "API", "LOCAL_RUNTIME": "Локальна модель", "GATEWAY": "Шлюз", "SUPPORTED": "Підтримується", "EXPERIMENTAL": "Експериментально", "CATALOG_ONLY": "Лише в каталозі"},
            "en": {},
        }.get(self.language, {})
        integration = states.get(profile.integration_type, profile.integration_type)
        support_state = states.get(profile.support_status, profile.support_status.replace("_", " ").title())
        self.detail.setText(
            f"<b>{profile.display_name}</b><br>"
            f"{connection}: {integration}<br>"
            f"{support}: {support_state}<br>"
            f"{platforms}: {', '.join(profile.supported_os)}<br>"
            f"{source}: {profile.official_url or '-'}<br><br>{hint}"
        )


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
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "provider"),
                {"ru": "Тип", "uk": "Тип", "en": "Type"}.get(language, "Тип"),
                {"ru": "Поддержка", "uk": "Підтримка", "en": "Support"}.get(language, "Поддержка"),
                tr(language, "install"),
                tr(language, "auth"),
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
        self.add_button = QPushButton({"ru": "Добавить ИИ", "uk": "Додати ШІ", "en": "Add AI"}.get(language, "Добавить ИИ"))
        self.add_button.clicked.connect(self.open_catalog)
        self.install_button = QPushButton({"ru": "Установить", "uk": "Встановити", "en": "Install"}.get(language, "Установить"))
        self.auth_button = QPushButton({"ru": "Войти", "uk": "Увійти", "en": "Sign in"}.get(language, "Войти"))
        self.update_button = QPushButton({"ru": "Обновить", "uk": "Оновити", "en": "Update"}.get(language, "Обновить"))
        self.uninstall_button = QPushButton({"ru": "Удалить CLI с компьютера", "uk": "Видалити CLI з комп'ютера", "en": "Uninstall CLI from computer"}.get(language, "Удалить CLI с компьютера"))
        self.key_button = QPushButton({"ru": "Задать ключ API", "uk": "Задати ключ API", "en": "Set API key"}.get(language, "Задать ключ API"))
        self.disconnect_button = QPushButton({"ru": "Удалить подключение", "uk": "Видалити підключення", "en": "Remove connection"}.get(language, "Удалить подключение"))
        self.docs_button = QPushButton({"ru": "Официальная документация", "uk": "Офіційна документація", "en": "Official documentation"}.get(language, "Официальная документация"))
        self.install_button.clicked.connect(lambda: self.run_action("install"))
        self.auth_button.clicked.connect(lambda: self.run_action("authenticate"))
        self.update_button.clicked.connect(lambda: self.run_action("update"))
        self.uninstall_button.clicked.connect(lambda: self.run_action("uninstall"))
        self.key_button.clicked.connect(self.configure_api_key)
        self.disconnect_button.clicked.connect(self.disconnect_provider)
        self.docs_button.clicked.connect(self.open_documentation)
        actions = QHBoxLayout()
        for button in (self.add_button, refresh, self.install_button, self.auth_button, self.update_button, self.key_button, self.disconnect_button, self.uninstall_button, self.docs_button):
            actions.addWidget(button)
        actions.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(language, "provider_page_note")))
        layout.addWidget(self.table, 2)
        layout.addLayout(actions)
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
                self._state_label(profile.integration_type),
                self._state_label(profile.support_status),
                self._state_label(health.installation_status),
                self._state_label(health.authentication_status),
                self._state_label(health.health_status),
                self._state_label(health.capability_status),
                ", ".join(assigned) or tr(self.language, "no"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, profile.provider_id)
                self.table.setItem(row, column, item)
        if profiles:
            self.table.selectRow(0)
        self._update_actions()

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
            f"{tr(self.language, 'display_name')}: {profile.display_name}",
            f"{self._text('integration')}: {self._state_label(profile.integration_type)}",
            f"{self._text('support')}: {self._state_label(profile.support_status)}",
            f"{self._text('official_source')}: {profile.official_url or tr(self.language, 'no')}",
            f"{self._text('catalog_class')}: {self._state_label(profile.catalog_class)}",
            f"{self._text('last_verified')}: {profile.last_verified or tr(self.language, 'no')}",
            f"{tr(self.language, 'required_capabilities')}: {', '.join(self._state_label(item) for item in profile.required_capabilities) or tr(self.language, 'no')}",
            f"{self._text('capability_matrix')}: "
            + ", ".join(
                f"{self._state_label(capability)}: {self._state_label(state)}"
                for capability, state in profile.capability_matrix.items()
            ),
            f"{tr(self.language, 'limitations')}: {self._limitations_text(profile)}",
            f"{self._text('credential')}: {self._credential_preview(profile)}",
            "",
            f"{tr(self.language, 'last_health')}:",
        ]
        if health is None:
            lines.append(tr(self.language, "not_checked"))
        else:
            lines.extend(
                [
                    f"{tr(self.language, 'install')}: {self._state_label(health.installation_status)}",
                    f"{tr(self.language, 'auth')}: {self._state_label(health.authentication_status)}",
                    f"{tr(self.language, 'access')}: {self._state_label(health.access_status)}",
                    f"{tr(self.language, 'health')}: {self._state_label(health.health_status)}",
                    f"{tr(self.language, 'capabilities')}: {self._state_label(health.capability_status)}",
                    f"{tr(self.language, 'diagnostics')}: {self._diagnostic_text(health)}",
                ]
            )
        self.detail.setPlainText("\n".join(lines))
        self._update_actions()

    def run_checks(self) -> None:
        for profile in self.registry.profiles():
            self.health_service.check_provider(profile.provider_id)
        self.refresh()

    def _selected_profile(self):
        provider_id = self.selected_provider_id()
        return self.registry.get(provider_id) if provider_id else None

    def _update_actions(self) -> None:
        profile = self._selected_profile()
        self.install_button.setEnabled(bool(profile and profile.install_command))
        self.auth_button.setEnabled(bool(profile and profile.auth_command))
        self.update_button.setEnabled(bool(profile and profile.update_command))
        self.uninstall_button.setEnabled(bool(profile and profile.uninstall_command))
        self.key_button.setEnabled(bool(profile and profile.credential_kind in {"API_KEY", "OPTIONAL_API_KEY"}))
        self.disconnect_button.setEnabled(bool(profile and profile.credential_kind in {"API_KEY", "OPTIONAL_API_KEY"}))
        self.docs_button.setEnabled(bool(profile and profile.official_url))

    def run_action(self, action: str) -> None:
        profile = self._selected_profile()
        if profile is None:
            return
        try:
            command = ProviderLifecycleService.command_for(profile, action)
        except ValueError as exc:
            QMessageBox.information(self, self._text("connections"), str(exc))
            return
        assigned = [
            employee.display_name
            for employee in self.management_service.list_employees()
            if employee.provider_id == profile.provider_id
        ]
        prompt = self._text("confirm_command").format(
            command=" ".join(command),
            source=profile.official_url or "-",
            platforms=", ".join(profile.supported_os),
            product=profile.display_name,
        )
        if action == "uninstall" and assigned:
            prompt += self._text("shared_warning").format(count=len(assigned), employees=", ".join(assigned))
        if QMessageBox.question(self, self._text("connections"), prompt) != QMessageBox.Yes:
            return
        try:
            ProviderLifecycleService.start(profile, action)
            self.health_service.database.log_event("provider_lifecycle_started", f"{profile.provider_id}:{action}")
        except OSError as exc:
            QMessageBox.warning(self, self._text("connections"), str(exc))

    def configure_api_key(self) -> None:
        profile = self._selected_profile()
        if profile is None or profile.credential_kind not in {"API_KEY", "OPTIONAL_API_KEY"}:
            return
        secret, ok = QInputDialog.getText(self, self._text("api_key"), self._text("api_key_prompt"), QLineEdit.Password)
        if not ok or not secret.strip():
            return
        try:
            reference = WindowsCredentialStore().write(profile.provider_id, secret.strip())
        except (SecureStorageUnavailable, OSError) as exc:
            QMessageBox.warning(self, self._text("api_key"), str(exc))
            return
        self.health_service.database.log_event("provider_credential_saved", f"{profile.provider_id}:{reference}")
        QMessageBox.information(self, self._text("api_key"), self._text("api_key_saved"))
        self.health_service.check_provider(profile.provider_id)
        self.refresh()

    def disconnect_provider(self) -> None:
        profile = self._selected_profile()
        if profile is None or profile.credential_kind not in {"API_KEY", "OPTIONAL_API_KEY"}:
            return
        if QMessageBox.question(self, self._text("connections"), self._text("disconnect_confirm")) != QMessageBox.Yes:
            return
        try:
            removed = WindowsCredentialStore().delete(profile.provider_id)
        except (SecureStorageUnavailable, OSError) as exc:
            QMessageBox.warning(self, self._text("connections"), str(exc))
            return
        self.health_service.database.log_event("provider_connection_removed", profile.provider_id)
        if removed:
            self.health_service.check_provider(profile.provider_id)
        self.refresh()

    def open_catalog(self) -> None:
        dialog = ProviderCatalogDialog(self.registry.profiles(), self.language, self)
        if dialog.exec() != QDialog.Accepted:
            return
        provider_id = dialog.selected_provider_id()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and str(item.data(Qt.UserRole)) == provider_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

    def open_documentation(self) -> None:
        profile = self._selected_profile()
        if profile is not None and profile.official_url:
            QDesktopServices.openUrl(QUrl(profile.official_url))

    def _text(self, key: str) -> str:
        values = {
            "ru": {"integration": "Способ подключения", "support": "Статус поддержки", "official_source": "Официальный источник", "catalog_class": "Официальный класс", "last_verified": "Проверено по документации", "capability_matrix": "Матрица возможностей", "credential": "Защищённый ключ", "connections": "ИИ и подключения", "confirm_command": "Продукт: {product}\nИсточник: {source}\nПлатформы: {platforms}\n\nБудет запущена официальная команда:\n{command}\n\nПродолжить?", "shared_warning": "\n\nЭтот движок используют сотрудники ({count}): {employees}. После удаления они не смогут отвечать через него.", "disconnect_confirm": "Удалить защищённый ключ и отключить это API от Team2050? Сотрудники сохранят назначение, но не смогут работать до нового подключения.", "api_key": "Ключ API", "api_key_prompt": "Введите ключ. Он будет сохранён в Диспетчере учётных данных Windows и не попадёт в базу Team2050.", "api_key_saved": "Ключ сохранён в защищённом хранилище Windows."},
            "uk": {"integration": "Спосіб підключення", "support": "Статус підтримки", "official_source": "Офіційне джерело", "catalog_class": "Офіційний клас", "last_verified": "Перевірено за документацією", "capability_matrix": "Матриця можливостей", "credential": "Захищений ключ", "connections": "ШІ та підключення", "confirm_command": "Продукт: {product}\nДжерело: {source}\nПлатформи: {platforms}\n\nБуде запущено офіційну команду:\n{command}\n\nПродовжити?", "shared_warning": "\n\nЦей рушій використовують співробітники ({count}): {employees}. Після видалення вони не зможуть відповідати через нього.", "disconnect_confirm": "Видалити захищений ключ і відключити цей API від Team2050? Призначення співробітників збережуться, але вони не працюватимуть до нового підключення.", "api_key": "Ключ API", "api_key_prompt": "Введіть ключ. Його буде збережено в Диспетчері облікових даних Windows, а не в базі Team2050.", "api_key_saved": "Ключ збережено в захищеному сховищі Windows."},
            "en": {"integration": "Connection type", "support": "Support status", "official_source": "Official source", "catalog_class": "Official class", "last_verified": "Documentation verified", "capability_matrix": "Capability matrix", "credential": "Secure key", "connections": "AI and connections", "confirm_command": "Product: {product}\nSource: {source}\nPlatforms: {platforms}\n\nThe official command will be started:\n{command}\n\nContinue?", "shared_warning": "\n\nEmployees use this engine ({count}): {employees}. They will not be able to answer through it after uninstall.", "disconnect_confirm": "Delete the protected key and disconnect this API from Team2050? Employee assignments remain but cannot run until reconnected.", "api_key": "API key", "api_key_prompt": "Enter the key. It will be stored in Windows Credential Manager, not in the Team2050 database.", "api_key_saved": "The key was stored in Windows Credential Manager."},
        }
        return values.get(self.language, values["ru"]).get(key, key)

    def _credential_preview(self, profile) -> str:
        if profile.credential_kind not in {"API_KEY", "OPTIONAL_API_KEY"}:
            return tr(self.language, "no")
        try:
            secret = WindowsCredentialStore().read(profile.provider_id)
        except (SecureStorageUnavailable, OSError):
            secret = None
        if not secret:
            return {"ru": "не задан", "uk": "не задано", "en": "not configured"}.get(self.language, "не задан")
        suffix = secret[-4:] if len(secret) >= 4 else "****"
        return f"••••••••{suffix}"

    def _state_label(self, value: str) -> str:
        labels = {
            "ru": {"CLI": "Командная строка", "API": "API", "LOCAL_RUNTIME": "Локальная модель", "GATEWAY": "Шлюз", "OFFICIAL_CLI": "Официальный CLI", "OFFICIAL_API": "Официальный API", "CLOUD_PLATFORM": "Облачная платформа", "CUSTOM_GATEWAY": "Внешний шлюз", "SUPPORTED": "Поддерживается", "EXPERIMENTAL": "Экспериментально", "CATALOG_ONLY": "Только в каталоге", "NOT_INSTALLED": "Не установлен", "DETECTED": "Обнаружен", "INSTALLED": "Установлен", "AUTHENTICATED": "Вход выполнен", "AUTHENTICATION_REQUIRED": "Нужен вход", "NOT_AUTHENTICATED": "Вход не выполнен", "NOT_CHECKED": "Не проверено", "ACCESS_AVAILABLE": "Доступ есть", "ACCESS_UNAVAILABLE": "Доступа нет", "INSTALLATION_REQUIRED": "Требуется установка", "NOT_READY": "Не готов", "READY": "Готов", "DEGRADED": "Ограниченно готов", "BLOCKED": "Заблокирован", "UNKNOWN": "Неизвестно", "PARTIAL": "Частично", "UNSUPPORTED": "Не поддерживается", "ADAPTER_REQUIRED": "Нужен адаптер", "AVAILABLE": "Доступно", "chat": "Чат", "structured_response": "Структурированный ответ", "file_read": "Чтение файлов", "file_write": "Запись файлов", "command_execution": "Выполнение команд", "long_context": "Большой контекст"},
            "uk": {"CLI": "Командний рядок", "API": "API", "LOCAL_RUNTIME": "Локальна модель", "GATEWAY": "Шлюз", "OFFICIAL_CLI": "Офіційний CLI", "OFFICIAL_API": "Офіційний API", "CLOUD_PLATFORM": "Хмарна платформа", "CUSTOM_GATEWAY": "Зовнішній шлюз", "SUPPORTED": "Підтримується", "EXPERIMENTAL": "Експериментально", "CATALOG_ONLY": "Лише в каталозі", "NOT_INSTALLED": "Не встановлено", "DETECTED": "Виявлено", "INSTALLED": "Встановлено", "AUTHENTICATED": "Вхід виконано", "AUTHENTICATION_REQUIRED": "Потрібен вхід", "NOT_AUTHENTICATED": "Вхід не виконано", "NOT_CHECKED": "Не перевірено", "ACCESS_AVAILABLE": "Доступ є", "ACCESS_UNAVAILABLE": "Доступу немає", "INSTALLATION_REQUIRED": "Потрібне встановлення", "NOT_READY": "Не готово", "READY": "Готово", "DEGRADED": "Обмежено готово", "BLOCKED": "Заблоковано", "UNKNOWN": "Невідомо", "PARTIAL": "Частково", "UNSUPPORTED": "Не підтримується", "ADAPTER_REQUIRED": "Потрібен адаптер", "AVAILABLE": "Доступно", "chat": "Чат", "structured_response": "Структурована відповідь", "file_read": "Читання файлів", "file_write": "Запис файлів", "command_execution": "Виконання команд", "long_context": "Великий контекст"},
            "en": {},
        }
        return labels.get(self.language, {}).get(value, value.replace("_", " ").title())

    def _limitations_text(self, profile) -> str:
        if not profile.known_limitations:
            return tr(self.language, "no")
        messages = {
            "ru": "Адаптер выполнения ещё не реализован и не прошёл проверку.",
            "uk": "Адаптер виконання ще не реалізовано та не перевірено.",
            "en": "; ".join(profile.known_limitations),
        }
        return messages.get(self.language, messages["ru"])

    def _diagnostic_text(self, health) -> str:
        if self.language == "en":
            return health.diagnostic or "No diagnostic details"
        labels = {
            "ru": {
                "READY": "Подключение проверено и готово к работе.",
                "DEGRADED": "Подключение найдено, но часть проверок ещё не пройдена.",
                "NOT_READY": "Подключение пока не готово. Проверьте установку и вход.",
                "BLOCKED": "Подключение заблокировано текущей конфигурацией.",
                "UNKNOWN": "Состояние подключения пока не определено.",
            },
            "uk": {
                "READY": "Підключення перевірено й готове до роботи.",
                "DEGRADED": "Підключення знайдено, але частину перевірок ще не пройдено.",
                "NOT_READY": "Підключення ще не готове. Перевірте встановлення та вхід.",
                "BLOCKED": "Підключення заблоковано поточною конфігурацією.",
                "UNKNOWN": "Стан підключення ще не визначено.",
            },
        }
        return labels.get(self.language, labels["ru"]).get(health.health_status, self._state_label(health.health_status))


class ProductDiagnosticsTab(QWidget):
    def __init__(self, service: ProductMetricsService | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Метрика", "Значение", "Статус", "Основание"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.routing_table = QTableWidget(0, 6)
        self.routing_table.setHorizontalHeaderLabels(["Время", "Режим", "Ответили", "Молчали", "Причина", "Версия"])
        self.routing_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.routing_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.thread_table = QTableWidget(0, 6)
        self.thread_table.setHorizontalHeaderLabels(["Обновлен", "Тред", "Владелец", "Задача", "Тема", "Ожидается"])
        self.thread_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.thread_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.question_table = QTableWidget(0, 6)
        self.question_table.setHorizontalHeaderLabels(["Обновлен", "Статус", "Назначено", "Вопрос", "Ответ", "Ответил"])
        self.question_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.question_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.send_pipeline_table = QTableWidget(0, 9)
        self.send_pipeline_table.setHorizontalHeaderLabels(["Время", "Трасса", "Пузырь, мс", "UI возвращён", "Сохранено", "Маршрут", "Провайдер", "Отрисовано", "Бюджет"])
        self.send_pipeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.send_pipeline_table.setEditTriggers(QTableWidget.NoEditTriggers)

        accept_question = QPushButton("Принять ответ")
        accept_question.clicked.connect(self.accept_question_answer)
        reopen_question = QPushButton("Вернуть в работу")
        reopen_question.clicked.connect(self.reopen_question)
        question_buttons = QHBoxLayout()
        question_buttons.addWidget(accept_question)
        question_buttons.addWidget(reopen_question)
        question_buttons.addStretch(1)

        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Локальная диагностика качества: маршрутизация, повторы, evidence, отмены и навыки. Данные не отправляются наружу."))
        layout.addWidget(self.metrics_table, 1)
        layout.addWidget(QLabel("Почему ответил этот сотрудник"))
        layout.addWidget(self.routing_table, 1)
        layout.addWidget(QLabel("Активные владельцы разговоров"))
        layout.addWidget(self.thread_table, 1)
        layout.addWidget(QLabel("Открытые и закрытые вопросы владельца"))
        layout.addWidget(self.question_table, 1)
        layout.addWidget(QLabel("Задержки отправки сообщений"))
        layout.addWidget(self.send_pipeline_table, 1)
        layout.addLayout(question_buttons)
        layout.addWidget(refresh)

    def refresh(self) -> None:
        if self.service is None:
            self.metrics_table.setRowCount(0)
            self.routing_table.setRowCount(0)
            self.thread_table.setRowCount(0)
            self.question_table.setRowCount(0)
            self.send_pipeline_table.setRowCount(0)
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

        traces = self.service.recent_send_pipeline_diagnostics()
        self.send_pipeline_table.setRowCount(len(traces))
        for row_index, trace in enumerate(traces):
            values = [trace.created_at, trace.trace_id, trace.bubble_ms, trace.event_loop_ms, trace.persisted_ms, trace.routing_ms, trace.provider_ms, trace.rendered_ms, trace.budget]
            for column, value in enumerate(values):
                self.send_pipeline_table.setItem(row_index, column, QTableWidgetItem(value))

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
            persona_id=str(self.persona.persona.currentData() or "").strip() or None,
            avatar_path=self.identity.selected_avatar_path(),
            full_name=self.identity.display_name.text().strip(),
            preferred_name=self.identity.preferred_name.text().strip(),
            informal_name=self.identity.informal_name.text().strip(),
            communication_profile=self.identity.selected_communication_profile(),
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
        self.preferred_name = QLineEdit()
        self.informal_name = QLineEdit()
        self.communication_profile: dict[str, object] = {}
        self.communication_controls: dict[str, QSpinBox] = {}
        communication_labels = {
            "ru": {"directness": "Прямота", "warmth": "Доброжелательность", "formality": "Формальность", "humor": "Юмор", "assertiveness": "Настойчивость", "verbosity": "Подробность", "initiative": "Инициативность", "emotionality": "Эмоциональность"},
            "uk": {"directness": "Прямота", "warmth": "Доброзичливість", "formality": "Формальність", "humor": "Гумор", "assertiveness": "Наполегливість", "verbosity": "Докладність", "initiative": "Ініціативність", "emotionality": "Емоційність"},
            "en": {"directness": "Directness", "warmth": "Warmth", "formality": "Formality", "humor": "Humor", "assertiveness": "Assertiveness", "verbosity": "Verbosity", "initiative": "Initiative", "emotionality": "Emotionality"},
        }.get(language, {})
        for key in ("directness", "warmth", "formality", "humor", "assertiveness", "verbosity", "initiative", "emotionality"):
            control = QSpinBox()
            control.setRange(0 if key == "humor" else 1, 5)
            control.setValue(1 if key in {"humor", "verbosity"} else 3)
            control.setSuffix(" / 5")
            self.communication_controls[key] = control
            control.valueChanged.connect(self._refresh_communication_summary)
        self.explanation_style = QComboBox()
        explanation_labels = {
            "ru": [("Коротко", "short"), ("Подробно", "detailed"), ("С примерами", "examples"), ("Технически", "technical")],
            "uk": [("Коротко", "short"), ("Докладно", "detailed"), ("З прикладами", "examples"), ("Технічно", "technical")],
            "en": [("Short", "short"), ("Detailed", "detailed"), ("With examples", "examples"), ("Technical", "technical")],
        }
        for label, value in explanation_labels.get(language, explanation_labels["ru"]):
            self.explanation_style.addItem(label, value)
        self.explanation_style.currentIndexChanged.connect(self._refresh_communication_summary)
        self.communication_summary = QLabel()
        self.communication_summary.setWordWrap(True)
        self.communication_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.gender = QComboBox()
        gender_labels = {
            "ru": [("Случайный", "random"), ("Женский", "female"), ("Мужской", "male")],
            "uk": [("Випадковий", "random"), ("Жіночий", "female"), ("Чоловічий", "male")],
            "en": [("Random", "random"), ("Female", "female"), ("Male", "male")],
        }
        for label, value in gender_labels.get(language, gender_labels["ru"]):
            self.gender.addItem(label, value)
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
        generate_personality = QPushButton(tr(language, "generate_personality"))
        generate_personality.setToolTip(tr(language, "generate_personality_hint"))
        generate_personality.clicked.connect(self.generate_personality)
        self.display_name.textChanged.connect(self.generate_id_if_empty)
        row = QHBoxLayout()
        row.addWidget(self.agent_id)
        row.addWidget(generate)
        form = QFormLayout(self)
        form.addRow(tr(language, "name"), self.display_name)
        form.addRow({"ru": "Как обращаться", "uk": "Як звертатися", "en": "Preferred name"}.get(language, "Как обращаться"), self.preferred_name)
        form.addRow({"ru": "Неформальное имя", "uk": "Неформальне ім'я", "en": "Informal name"}.get(language, "Неформальное имя"), self.informal_name)
        form.addRow(tr(language, "gender"), self.gender)
        form.addRow(tr(language, "agent_id"), row)
        form.addRow(tr(language, "description"), self.description)
        for key, control in self.communication_controls.items():
            form.addRow(communication_labels.get(key, key), control)
        form.addRow({"ru": "Стиль объяснений", "uk": "Стиль пояснень", "en": "Explanation style"}.get(language, "Стиль объяснений"), self.explanation_style)
        form.addRow({"ru": "Профиль общения", "uk": "Профіль спілкування", "en": "Communication profile"}.get(language, "Профиль общения"), self.communication_summary)
        form.addRow(tr(language, "avatar"), avatar_row)
        form.addRow("", self.avatar)
        form.addRow("", generate_personality)
        form.addRow(tr(language, "status"), self.lifecycle)
        self._apply_avatar_choice()
        self._refresh_communication_summary()

    def generate_id_if_empty(self) -> None:
        if not self.agent_id.text().strip():
            self.generate_id()

    def generate_id(self) -> None:
        self.agent_id.setText(self.service.generate_agent_id(self.display_name.text()))

    def generate_personality(self) -> None:
        identity = generate_identity(
            self.language,
            str(self.gender.currentData() or "random"),
            self.avatar_dir,
        )
        self.display_name.setText(identity.name)
        self.description.setPlainText(identity.biography)
        self.preferred_name.setText(identity.preferred_name)
        self.informal_name.setText(identity.informal_name)
        self.communication_profile = dict(identity.communication_profile)
        for key, control in self.communication_controls.items():
            control.setValue(int(identity.communication_profile.get(key, control.value())))
        explanation_index = self.explanation_style.findData(identity.communication_profile.get("explanation_style", "short"))
        if explanation_index >= 0:
            self.explanation_style.setCurrentIndex(explanation_index)
        if identity.avatar_path:
            self.avatar.setText(identity.avatar_path)
            index = self.avatar_choice.findData(identity.avatar_path)
            if index >= 0:
                self.avatar_choice.setCurrentIndex(index)
        self.generate_id()

    def selected_avatar_path(self) -> str | None:
        return self.avatar.text().strip() or None

    def selected_communication_profile(self) -> dict[str, object]:
        profile = {key: control.value() for key, control in self.communication_controls.items()}
        profile["explanation_style"] = str(self.explanation_style.currentData() or "short")
        profile["disagreement_style"] = str(self.communication_profile.get("disagreement_style", "evidence_first"))
        return profile

    def _refresh_communication_summary(self) -> None:
        profile = {key: control.value() for key, control in self.communication_controls.items()}
        scale = {
            "ru": (("сдержанное", "живое"), ("официальное", "дружеское"), ("кратко", "подробно")),
            "uk": (("стримане", "живе"), ("офіційне", "дружнє"), ("коротко", "докладно")),
            "en": (("reserved", "lively"), ("formal", "friendly"), ("brief", "detailed")),
        }.get(self.language)
        if scale is None:
            scale = (("сдержанное", "живое"), ("официальное", "дружеское"), ("кратко", "подробно"))
        tone = scale[0][1] if profile.get("emotionality", 3) >= 4 else scale[0][0]
        relation = scale[1][1] if profile.get("formality", 3) <= 2 else scale[1][0]
        detail = scale[2][1] if profile.get("verbosity", 2) >= 3 else scale[2][0]
        self.communication_summary.setText(
            f"{tone}; {relation}; {detail}; {self.explanation_style.currentText().lower()}"
        )

    def _load_avatar_choices(self) -> None:
        self.avatar_choice.addItem(tr(self.language, "not_set"), "")
        if self.avatar_dir and self.avatar_dir.exists():
            for path in list_avatar_files(self.avatar_dir):
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
                    "woman": "женщина",
                    "man": "мужчина",
                    "realistic": "реализм",
                    "cartoon": "мульт",
                    "cat": "кот",
                    "dog": "собака",
                    "tabby": "полосатый",
                    "ginger": "рыжий",
                    "golden": "ретривер",
                    "corgi": "корги",
                    "reaction": "мем",
                },
                "uk": {
                    "woman": "жінка",
                    "man": "чоловік",
                    "realistic": "реалізм",
                    "cartoon": "мульт",
                    "cat": "кіт",
                    "dog": "собака",
                    "tabby": "смугастий",
                    "ginger": "рудий",
                    "golden": "ретривер",
                    "corgi": "коргі",
                    "reaction": "мем",
                },
                "en": {},
            }
            translated = [vocabulary.get(language, vocabulary["ru"]).get(word, word) for word in words]
            return f"{number} - {', '.join(translated)}".strip(" -")
        labels = {
            "ru": {
                "realistic-female": "Реализм: женщина",
                "realistic-male": "Реализм: мужчина",
                "cartoon-female": "Мульт: женщина",
                "cartoon-male": "Мульт: мужчина",
            },
            "uk": {
                "realistic-female": "Реалізм: жінка",
                "realistic-male": "Реалізм: чоловік",
                "cartoon-female": "Мульт: жінка",
                "cartoon-male": "Мульт: чоловік",
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
            self._status_text(provider_id, health)
        )

    def _status_text(self, provider_id: str, health) -> str:
        profile = self.provider_health_service.registry.get(provider_id)
        support = profile.support_status if profile is not None else "CATALOG_ONLY"
        labels = {
            "ru": {"SUPPORTED": "поддерживается", "EXPERIMENTAL": "экспериментально", "CATALOG_ONLY": "только в каталоге", "INSTALLED": "установлен", "NOT_INSTALLED": "не установлен", "AUTHENTICATED": "вход выполнен", "AUTHENTICATION_REQUIRED": "нужен вход", "NOT_AUTHENTICATED": "вход не выполнен", "READY": "готов", "NOT_READY": "не готов", "DEGRADED": "ограниченно готов", "BLOCKED": "заблокирован", "UNKNOWN": "неизвестно"},
            "uk": {"SUPPORTED": "підтримується", "EXPERIMENTAL": "експериментально", "CATALOG_ONLY": "лише в каталозі", "INSTALLED": "встановлено", "NOT_INSTALLED": "не встановлено", "AUTHENTICATED": "вхід виконано", "AUTHENTICATION_REQUIRED": "потрібен вхід", "NOT_AUTHENTICATED": "вхід не виконано", "READY": "готово", "NOT_READY": "не готово", "DEGRADED": "обмежено готово", "BLOCKED": "заблоковано", "UNKNOWN": "невідомо"},
            "en": {},
        }.get(self.language, {})
        label = lambda value: labels.get(value, value.replace("_", " ").title())
        prefixes = {"ru": ("Поддержка", "Установка", "Авторизация", "Готовность"), "uk": ("Підтримка", "Встановлення", "Авторизація", "Готовність"), "en": ("Support", "Installation", "Authentication", "Readiness")}
        support_title, install_title, auth_title, health_title = prefixes.get(self.language, prefixes["ru"])
        return f"{support_title}: {label(support)}\n{install_title}: {label(health.installation_status)}\n{auth_title}: {label(health.authentication_status)}\n{health_title}: {label(health.health_status)}"


class PersonaPage(QWizardPage):
    def __init__(self, language: str) -> None:
        super().__init__()
        self.setTitle(tr(language, "persona"))
        self.persona = QComboBox()
        fill_persona_combo(self.persona, language)
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
        apply_team_dialog_chrome(self, minimum_width=640)
        self.service = service
        self.agent_id = agent_id
        self.language = language
        self.avatar_dir = avatar_dir
        self.employee = service.get_employee(agent_id)
        self.row = service.database.get_agent_profile(agent_id)
        if self.employee is None or self.row is None:
            raise ValueError("unknown employee")
        self.setWindowTitle(tr(language, "edit"))
        self.resize(820, 720)
        self.display_name = QLineEdit(self.employee.display_name)
        self.preferred_name = QLineEdit(str(self.row["preferred_name"] or ""))
        self.informal_name = QLineEdit(str(self.row["informal_name"] or ""))
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
        fill_persona_combo(self.persona, language)
        if self.employee.persona_id:
            index = self.persona.findData(self.employee.persona_id)
            if index < 0:
                self.persona.addItem(self.employee.persona_id, self.employee.persona_id)
                index = self.persona.count() - 1
            self.persona.setCurrentIndex(index)
        try:
            communication_profile = json.loads(str(self.row["communication_profile"] or "{}"))
        except (TypeError, json.JSONDecodeError):
            communication_profile = {}
        self.communication_profile = communication_profile if isinstance(communication_profile, dict) else {}
        self.communication_controls: dict[str, QSpinBox] = {}
        communication_labels = {
            "ru": {"directness": "Прямота", "warmth": "Доброжелательность", "formality": "Формальность", "humor": "Юмор", "assertiveness": "Настойчивость", "verbosity": "Подробность", "initiative": "Инициативность", "emotionality": "Эмоциональность"},
            "uk": {"directness": "Прямота", "warmth": "Доброзичливість", "formality": "Формальність", "humor": "Гумор", "assertiveness": "Наполегливість", "verbosity": "Докладність", "initiative": "Ініціативність", "emotionality": "Емоційність"},
            "en": {"directness": "Directness", "warmth": "Warmth", "formality": "Formality", "humor": "Humor", "assertiveness": "Assertiveness", "verbosity": "Verbosity", "initiative": "Initiative", "emotionality": "Emotionality"},
        }.get(language, {})
        for key in ("directness", "warmth", "formality", "humor", "assertiveness", "verbosity", "initiative", "emotionality"):
            control = QSpinBox()
            control.setRange(0 if key == "humor" else 1, 5)
            control.setValue(int(self.communication_profile.get(key, 1 if key in {"humor", "verbosity"} else 3)))
            control.setSuffix(" / 5")
            self.communication_controls[key] = control
        self.explanation_style = QComboBox()
        explanation_labels = {
            "ru": [("Коротко", "short"), ("Подробно", "detailed"), ("С примерами", "examples"), ("Технически", "technical")],
            "uk": [("Коротко", "short"), ("Докладно", "detailed"), ("З прикладами", "examples"), ("Технічно", "technical")],
            "en": [("Short", "short"), ("Detailed", "detailed"), ("With examples", "examples"), ("Technical", "technical")],
        }
        for label, value in explanation_labels.get(language, explanation_labels["ru"]):
            self.explanation_style.addItem(label, value)
        explanation_index = self.explanation_style.findData(self.communication_profile.get("explanation_style", "short"))
        self.explanation_style.setCurrentIndex(max(0, explanation_index))
        self.disagreement_style = QComboBox()
        disagreement_labels = {
            "ru": [("Сначала факты", "evidence_first"), ("Дипломатично", "diplomatic"), ("Прямо", "direct")],
            "uk": [("Спочатку факти", "evidence_first"), ("Дипломатично", "diplomatic"), ("Прямо", "direct")],
            "en": [("Evidence first", "evidence_first"), ("Diplomatic", "diplomatic"), ("Direct", "direct")],
        }
        for label, value in disagreement_labels.get(language, disagreement_labels["ru"]):
            self.disagreement_style.addItem(label, value)
        disagreement_index = self.disagreement_style.findData(self.communication_profile.get("disagreement_style", "evidence_first"))
        self.disagreement_style.setCurrentIndex(max(0, disagreement_index))
        regenerate_communication = QPushButton(
            {"ru": "Сгенерировать стиль общения", "uk": "Згенерувати стиль спілкування", "en": "Generate communication style"}.get(language, "Сгенерировать стиль общения")
        )
        regenerate_communication.clicked.connect(self._regenerate_communication_profile)
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
        general_tab = QWidget()
        general_form = QFormLayout(general_tab)
        general_form.addRow(tr(language, "agent_id"), QLabel(self.agent_id))
        general_form.addRow(tr(language, "name"), self.display_name)
        general_form.addRow({"ru": "Как обращаться", "uk": "Як звертатися", "en": "Preferred name"}.get(language, "Как обращаться"), self.preferred_name)
        general_form.addRow({"ru": "Неформальное имя", "uk": "Неформальне ім'я", "en": "Informal name"}.get(language, "Неформальное имя"), self.informal_name)
        general_form.addRow(tr(language, "description"), self.description)
        general_form.addRow(tr(language, "avatar"), avatar_row)
        general_form.addRow("", self.avatar)
        general_form.addRow(tr(language, "provider"), self.provider)
        general_form.addRow(tr(language, "persona"), self.persona)
        communication_tab = QWidget()
        communication_form = QFormLayout(communication_tab)
        for key, control in self.communication_controls.items():
            communication_form.addRow(communication_labels.get(key, key), control)
        communication_form.addRow(
            {"ru": "Стиль объяснений", "uk": "Стиль пояснень", "en": "Explanation style"}.get(language, "Стиль объяснений"),
            self.explanation_style,
        )
        communication_form.addRow(
            {"ru": "Стиль несогласия", "uk": "Стиль незгоди", "en": "Disagreement style"}.get(language, "Стиль несогласия"),
            self.disagreement_style,
        )
        communication_form.addRow("", regenerate_communication)
        access_tab = QWidget()
        access_layout = QVBoxLayout(access_tab)
        access_layout.addWidget(QLabel(tr(language, "roles")))
        access_layout.addWidget(self.roles)
        access_layout.addWidget(QLabel(tr(language, "direct_grants")))
        access_layout.addWidget(self.permissions)
        access_layout.addWidget(QLabel(tr(language, "direct_denies")))
        access_layout.addWidget(self.denies)
        tabs = QTabWidget()
        tabs.addTab(general_tab, {"ru": "Профиль", "uk": "Профіль", "en": "Profile"}.get(language, "Профиль"))
        tabs.addTab(communication_tab, {"ru": "Общение", "uk": "Спілкування", "en": "Communication"}.get(language, "Общение"))
        tabs.addTab(access_tab, {"ru": "Роли и права", "uk": "Ролі та права", "en": "Roles and permissions"}.get(language, "Роли и права"))
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
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
            for path in list_avatar_files(self.avatar_dir):
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

    def _regenerate_communication_profile(self) -> None:
        profile = generate_identity(self.language, "random", self.avatar_dir).communication_profile
        self.communication_profile = dict(profile)
        for key, control in self.communication_controls.items():
            control.setValue(int(profile.get(key, control.value())))
        explanation_index = self.explanation_style.findData(profile.get("explanation_style", "short"))
        if explanation_index >= 0:
            self.explanation_style.setCurrentIndex(explanation_index)
        disagreement_index = self.disagreement_style.findData(profile.get("disagreement_style", "evidence_first"))
        if disagreement_index >= 0:
            self.disagreement_style.setCurrentIndex(disagreement_index)

    def selected_communication_profile(self) -> dict[str, object]:
        profile = dict(self.communication_profile)
        profile.update({key: control.value() for key, control in self.communication_controls.items()})
        profile["explanation_style"] = str(self.explanation_style.currentData() or "short")
        profile["disagreement_style"] = str(self.disagreement_style.currentData() or "evidence_first")
        return profile

    def save(self) -> None:
        try:
            preview = self.service.update_employee(
                self.agent_id,
                display_name=self.display_name.text().strip(),
                description=self.description.toPlainText().strip(),
                provider_id=str(self.provider.currentData()),
                persona_id=str(self.persona.currentData() or "").strip() or None,
                avatar_path=self.avatar.text().strip() or None,
                preferred_name=self.preferred_name.text().strip(),
                informal_name=self.informal_name.text().strip(),
                communication_profile=self.selected_communication_profile(),
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
            "owner_authority_required": "Требуются права владельца организации.",
            "duplicate_agent_id": "Такой ID сотрудника уже существует.",
            "active_employee_requires_available_provider": "Активному сотруднику нужен доступный провайдер.",
            "optimistic_lock_conflict": "Профиль уже изменился. Обновите карточку и повторите.",
            "FOREIGN KEY constraint failed": tr(language, "foreign_key_error"),
            "invalid_role": tr(language, "unknown_role"),
            "unknown_role": tr(language, "unknown_role"),
            "invalid_provider": tr(language, "unknown_provider"),
            "unknown_agent_id": tr(language, "unknown_agent"),
            "empty_display_name": tr(language, "empty_display_name"),
            "agent_id_must_be_stable_agent_id": tr(language, "agent_id_required"),
        },
        "uk": {
            "owner_authority_required": "Потрібні права власника організації.",
            "duplicate_agent_id": "Такий ID співробітника вже існує.",
            "active_employee_requires_available_provider": "Активному співробітнику потрібен доступний провайдер.",
            "optimistic_lock_conflict": "Профіль уже змінився. Оновіть картку і повторіть.",
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
