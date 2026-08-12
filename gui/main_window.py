from __future__ import annotations

import logging
import re
from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, QSettings, QTimer, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.agent_directory import ChatAgent, ROLE_NAMES, agent_id_from_key, get_chat_agent, list_chat_agents, mention_tokens
from core.agent_router import AgentRouter
from core.artifact_service import ArtifactService
from core.auth_service import AuthService
from core.autonomy import AutonomyRequest, has_handoff_intent, is_stop_command, parse_autonomy_request
from core.codex_client import CodexClient
from core.build_info import build_label
from core.claim_evidence import ClaimEvidenceValidator
from core.chat_sound_service import ChatSoundService
from core.config_repository import ConfigurationRepository
from core.conversation_mode import ConversationMode, infer_mode
from core.conversation_thread_service import ConversationThreadService
from core.database import Database
from core.director_service import DirectorAction, DirectorService
from core.gemini_client import GeminiClient
from core.identity_service import IdentityError, IdentityService
from core.finding_service import FindingService
from core.knowledge_service import KnowledgeService
from core.knowledge_application_service import KnowledgeApplicationService
from core.learning_evidence_service import LearningEvidenceService
from core.learning_manager_service import LearningManagerService
from core.management_service import ManagementService
from core.memory_service import MemoryService
from core.path_guard import PathGuardError
from core.prompt_builder import PromptBuilder
from core.product_metrics_service import ProductMetricsService
from core.provider_service import (
    CodexProviderAdapter,
    GeminiProviderAdapter,
    ProviderHealthService,
    ProviderProvisioningService,
    ProviderRegistry,
)
from core.response_cleaner import ResponseCleaner
from core.response_latency import ResponseLatencyPolicy
from core.response_splitter import ResponseSplitter
from core.settings_service import SettingsService
from core.skill_progress_service import SkillProgressService
from core.skill_package_service import SkillPackageService
from core.skill_service import SkillService
from core.standards_service import StandardsService
from core.structured_response import ParsedAgentResponse, parse_agent_response
from core.team_routing import ManualRouting, TeamRouter, TeamRoutingDecision
from core.thread_question_service import ThreadQuestionService
from core.tool_access import agent_can_use_local_tools
from core.task_orchestrator import TaskOrchestrator
from core.task_state_service import TaskStateService
from core.workspace_service import WorkspaceService
from core.universal_platform_service import UniversalPlatformService
from core.work_context_service import (
    ActiveWorkContext,
    AgentExecutionContract,
    ArtifactReferentResolver,
    IntentResolver,
    IntentType,
    OutputValidator,
    UserIntent,
    WorkContextService,
)
from gui.chat_widget import ChatWidget
from gui.director_console import DirectorConsoleDialog, OrganizationActivationWizard
from gui.login_dialog import show_install_instructions
from gui.localization import catalog_label, role_label
from gui.settings_dialog import SettingsDialog
from gui.theme import ThemeBackdrop, ThemeManager
from gui.worker import GenerateWorker


class MainWindow(QMainWindow):
    def __init__(self, settings_service: SettingsService, logger: logging.Logger) -> None:
        super().__init__()
        self.startup_state = "APP_START"
        self.startup_history: list[str] = ["APP_START"]
        self.conversation_id: int | None = None
        self.active_organization_id: str | None = None
        self.conversation_mode = ConversationMode.SOCIAL
        self.current_thread_id: str | None = None
        self.current_task_id: str | None = None
        self.setWindowTitle("Team2050 — Отдел важных дел")
        self.setMinimumSize(760, 560)
        self.resize(1280, 800)
        self.settings_service = settings_service
        self.paths = settings_service.paths
        self.logger = logger
        self.settings = settings_service.load()
        self.chat_sound_service = ChatSoundService(self.paths.data_dir / "sounds", self.settings)
        self._set_startup_state("SETTINGS_READY")

        self.database = Database(self.paths.database_path)
        self.database.initialize()
        self._set_startup_state("DATABASE_READY")
        self.management_repository = ConfigurationRepository(self.paths.management_config_dir)
        self.management_service = ManagementService(self.database, self.management_repository)
        self.management_service.ensure_foundations()
        self._set_startup_state("MANAGEMENT_READY")
        self.database.ensure_organization_conversations()
        self.active_organization_id = self.database.get_active_organization_id()
        if self.active_organization_id is None:
            first_active = next(
                (row for row in self.database.list_organizations() if str(row["status"]).upper() == "ACTIVE"),
                None,
            )
            if first_active is not None:
                self.database.set_active_organization(str(first_active["id"]))
                self.active_organization_id = str(first_active["id"])
        if self.active_organization_id:
            organization = next(
                (row for row in self.database.list_organizations() if str(row["id"]) == self.active_organization_id),
                None,
            )
            title = str(organization["name"]) if organization is not None else "Командный чат"
            self.conversation_id = self.database.ensure_organization_conversation(self.active_organization_id, title)
        else:
            self.conversation_id = (
                self.database.ensure_general_conversation()
                if self.database.list_organizations()
                else self.database.ensure_single_conversation()
            )
        if self.conversation_id is None:
            raise RuntimeError("Не удалось разрешить рабочий разговор при запуске")
        self._set_startup_state("CONVERSATION_RESOLVED")
        self._set_startup_state("ORGANIZATION_RESOLVED")
        self.agent_router = AgentRouter(self.database)
        self.team_router = TeamRouter(str(self.settings.get("general_chat_response", "SINGLE")))
        self.task_state_service = TaskStateService(self.database)
        self.task_orchestrator = TaskOrchestrator(self.database, self.task_state_service, self.agent_router)
        self.task_orchestrator.ensure_project()
        self.director_service = DirectorService(self.database)
        self.universal_platform_service = UniversalPlatformService(
            self.database,
            management_service=self.management_service,
            workspace_root=self.paths.workspace_root,
            conversation_id=self.conversation_id,
            avatar_dir=self.paths.avatar_dir,
            identity_language=str(self.settings.get("interface_language", "ru")),
        )
        # Keep clean install limited to built-in presets and role templates;
        # domain/demo professions are loaded only when requested in the console.
        self.universal_platform_service.seed_management_library()
        self.memory_service = MemoryService(self.database)
        self.skill_service = SkillService(self.paths.skills_path)
        self.skill_package_service = SkillPackageService(self.database)
        self.knowledge_service = KnowledgeService(self.database)
        self.knowledge_application_service = KnowledgeApplicationService(self.database)
        self.learning_evidence_service = LearningEvidenceService(self.database)
        self.learning_manager_service = LearningManagerService(
            self.database,
            self.learning_evidence_service,
            self.skill_package_service,
        )
        self.standards_service = StandardsService(self.database)
        self.finding_service = FindingService(self.database)
        self.claim_validator = ClaimEvidenceValidator()
        self.identity_service = IdentityService(self.paths.identity_path, self.paths.identity_backup_path, logger)
        workspace_root = Path(self.settings.get("workspace_root") or self.paths.workspace_root)
        self.workspace_service = WorkspaceService(workspace_root)
        self.workspace_service.ensure()
        self.settings["workspace_root"] = str(self.workspace_service.root)
        self.settings_service.save(self.settings)
        self.artifact_service = ArtifactService(self.database, self.workspace_service.root)
        self.codex_client = CodexClient(
            workspace=self.workspace_service.chat_runtime,
            timeout_seconds=int(self.settings.get("codex_timeout_seconds", 180)),
            logger=logger,
        )
        self.gemini_client = GeminiClient(
            workspace=self.workspace_service.gemini_runtime,
            timeout_seconds=int(self.settings.get("codex_timeout_seconds", 180)),
            logger=logger,
        )
        self.provider_registry = ProviderRegistry(self.database)
        self.provider_registry.ensure_defaults()
        self.provider_health_service = ProviderHealthService(
            self.database,
            self.provider_registry,
            {
                "CODEX_CLI": CodexProviderAdapter(self.codex_client),
                "GEMINI_CLI": GeminiProviderAdapter(self.gemini_client),
            },
        )
        self.provider_provisioning_service = ProviderProvisioningService(
            self.database,
            self.provider_registry,
            self.provider_health_service,
        )
        self.provider_provisioning_service.ensure_assignments_for_existing_agents()
        self.auth_service = AuthService(self.codex_client)
        self.skill_progress_service = SkillProgressService(self.database, self.skill_service, self.workspace_service.root)
        self.product_metrics_service = ProductMetricsService(self.database, self.skill_progress_service)
        self.thread_service = ConversationThreadService(self.database, self.conversation_id)
        self.current_thread_id = self.thread_service.thread_id
        self.last_addressed_agent_keys = self.thread_service.owner_keys()
        self.last_routing_decision = None
        self.thread_question_service = ThreadQuestionService(self.database, self.conversation_id)
        self.work_context_service = WorkContextService(self.database, self.conversation_id, self.thread_service.thread_id)
        self.intent_resolver = IntentResolver()
        self.artifact_referent_resolver = ArtifactReferentResolver(self.database)
        self.output_validator = OutputValidator()
        self.current_work_intent = UserIntent(IntentType.UNKNOWN, IntentType.UNKNOWN.value)
        self.current_work_reference = None
        self.current_execution_contract: AgentExecutionContract | None = None
        self.worker: GenerateWorker | None = None
        self.active_workers: dict[str, GenerateWorker] = {}
        self.current_agent_key = ""
        self.pending_agent_keys: list[str] = []
        self.authorized_worker_keys: set[str] = set()
        self.pending_user_message = ""
        self.last_peer_context = ""
        self.last_addressed_agent_keys: list[str] = self.thread_service.owner_keys()
        self.last_routing_decision: TeamRoutingDecision | None = None
        self.autonomous_active = False
        self.autonomous_goal = ""
        self.autonomous_complete_on_goal = False
        self.autonomous_turn = 0
        self.autonomous_fingerprints: list[str] = []
        self.autonomous_agent_keys: list[str] = []
        self.active_director_plan_id: str | None = None
        self.active_director_action: DirectorAction | None = None
        self.exchange_turn = 0
        self.exchange_turn_limit = 0
        self.exchange_responded_agent_keys: set[str] = set()
        self.exchange_fingerprints: list[str] = []
        self.pending_contextual_handoffs: list[tuple[str, str]] = []
        self.queued_user_message: tuple[str, int] | None = None
        self.interrupting_current_run = False
        self.cancellation_in_progress = False
        self.live_guidance: list[str] = []
        self.identity_ok = False
        self.codex_authorized = False
        self.codex_version = "неизвестно"
        self.gemini_version = "неизвестно"
        self._set_startup_state("CHAT_SERVICES_READY")
        self.latency_soft_timer = QTimer(self)
        self.latency_soft_timer.setSingleShot(True)
        self.latency_soft_timer.timeout.connect(lambda: self._show_response_latency_warning("soft"))
        self.latency_extended_timer = QTimer(self)
        self.latency_extended_timer.setSingleShot(True)
        self.latency_extended_timer.timeout.connect(lambda: self._show_response_latency_warning("extended"))
        self.latency_timeout_timer = QTimer(self)
        self.latency_timeout_timer.setSingleShot(True)
        self.latency_timeout_timer.timeout.connect(self._response_latency_timeout)

        self._build_ui()
        self._restore_window_state()
        self.apply_theme()
        self._first_start_checks()
        self.load_conversation()
        self._refresh_work_context_strip()
        self._update_workspace_status()
        self._set_startup_state("MAINWINDOW_READY")
        self._set_startup_state("USER_INTERACTIVE")

    def _set_startup_state(self, state: str) -> None:
        self.startup_state = state
        if not self.startup_history or self.startup_history[-1] != state:
            self.startup_history.append(state)
        if hasattr(self, "logger"):
            self.logger.info("startup_state=%s conversation_id=%s", state, self.conversation_id)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QWidget()
        top.setObjectName("topBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(22, 12, 22, 12)
        brand = QLabel("Отдел важных дел")
        logo = QLabel("R")
        logo.setObjectName("appLogo")
        logo.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(logo)
        brand.setObjectName("brand")
        brand_column = QVBoxLayout()
        brand_column.setSpacing(1)
        subtitle = QLabel("Рабочий чат команды")
        subtitle.setObjectName("brandSubtitle")
        brand_column.addWidget(brand)
        brand_column.addWidget(subtitle)
        top_layout.addLayout(brand_column)
        self.organization_selector = QComboBox()
        self.organization_selector.setObjectName("organizationSelector")
        self.organization_selector.setMinimumWidth(170)
        self.organization_selector.setToolTip("Выберите рабочую команду и её чат")
        self.organization_selector.currentIndexChanged.connect(self._switch_organization)
        top_layout.addWidget(self.organization_selector)
        self.codex_status_label = QLabel("Codex: проверка")
        self.codex_status_label.setObjectName("statusPill")
        self.gemini_status_label = QLabel("Gemini: проверка")
        self.gemini_status_label.setObjectName("statusPill")
        top_layout.addStretch(1)
        top_layout.addWidget(self.codex_status_label)
        top_layout.addWidget(self.gemini_status_label)
        top_layout.addStretch(1)
        self.auth_button = QPushButton("Войти")
        self.auth_button.setObjectName("smallAction")
        self.auth_button.clicked.connect(self._auth_action)
        top_layout.addWidget(self.auth_button)
        self.director_button = QPushButton("Команда")
        self.director_button.setObjectName("smallAction")
        self.director_button.setToolTip("Центр управления командой")
        self.director_button.clicked.connect(self.show_director_console_preview)
        top_layout.addWidget(self.director_button)
        self.routing_debug_button = QPushButton("Маршрут")
        self.routing_debug_button.setObjectName("smallAction")
        self.routing_debug_button.setToolTip("Почему выбран этот сотрудник")
        self.routing_debug_button.clicked.connect(self.show_routing_diagnostic)
        self.work_context_button = QPushButton("Контекст")
        self.work_context_button.setObjectName("smallAction")
        self.work_context_button.setToolTip("Показать текущую задачу и рабочий артефакт")
        self.work_context_button.clicked.connect(self.show_work_context_diagnostic)
        if bool(self.settings.get("developer_mode", False)):
            top_layout.addWidget(self.routing_debug_button)
            top_layout.addWidget(self.work_context_button)
        self.top_settings_button = QToolButton()
        self.top_settings_button.setText("⚙")
        self.top_settings_button.setToolTip("Настройки")
        self.top_settings_button.clicked.connect(self.open_settings)
        top_layout.addWidget(self.top_settings_button)
        outer.addWidget(top)

        self.work_context_label = QLabel()
        self.work_context_label.setObjectName("workContextStrip")
        self.work_context_label.setWordWrap(True)
        self.work_context_label.setMinimumHeight(28)
        outer.addWidget(self.work_context_label)

        self.chat_panel = self._build_chat_panel()
        outer.addWidget(self.chat_panel, 1)

        footer = QWidget()
        footer.setObjectName("statusBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 5, 18, 5)
        self.workspace_status_label = QLabel()
        self.workspace_status_label.setObjectName("tiny")
        footer_layout.addWidget(self.workspace_status_label, 1)
        footer_layout.addWidget(QLabel(build_label()))
        outer.addWidget(footer)
        self.setCentralWidget(root)

    def _build_navigation_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("navPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        logo = QLabel("◈")
        logo.setObjectName("brandMark")
        title = QLabel("TEAM\n2050")
        title.setObjectName("brand")
        collapse = QToolButton()
        collapse.setText("‹")
        collapse.setToolTip("Свернуть навигацию")
        collapse.clicked.connect(self._toggle_navigation)
        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(collapse)
        layout.addLayout(header)

        conversation = QFrame()
        conversation.setObjectName("card")
        conversation_layout = QVBoxLayout(conversation)
        conversation_layout.setContentsMargins(10, 10, 10, 10)
        conversation_layout.addWidget(QLabel("КОМАНДНЫЙ РАЗГОВОР"))
        self.team_roster_layout = QVBoxLayout()
        conversation_layout.addLayout(self.team_roster_layout)
        subtitle = QLabel("Один рабочий чат, активные сотрудники")
        subtitle.setObjectName("tiny")
        conversation_layout.addWidget(subtitle)
        layout.addWidget(conversation)

        layout.addStretch(1)

        profile = QFrame()
        profile.setObjectName("card")
        profile_layout = QHBoxLayout(profile)
        avatar = QLabel("ВЫ")
        avatar.setObjectName("brandMark")
        profile_layout.addWidget(avatar)
        profile_text = QVBoxLayout()
        profile_text.addWidget(QLabel("Владелец"))
        profile_text.addWidget(QLabel("Codex + Gemini по задачам", objectName="tiny"))
        profile_layout.addLayout(profile_text, 1)
        self.auth_button = QPushButton("Войти")
        self.auth_button.setObjectName("smallAction")
        self.auth_button.clicked.connect(self._auth_action)
        profile_layout.addWidget(self.auth_button)
        settings = QToolButton()
        settings.setText("⚙")
        settings.setToolTip("Настройки и вход")
        settings.clicked.connect(self.open_settings)
        profile_layout.addWidget(settings)
        layout.addWidget(profile)
        return panel

    def _build_chat_panel(self) -> QWidget:
        panel = ThemeBackdrop(str(self.settings.get("theme", "dark")))
        panel.setObjectName("chatPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.chat = ChatWidget(str(self.settings.get("interface_language", "ru")))
        self._refresh_chat_agents()
        self.chat.send_requested.connect(self.send_message)
        self.chat.stop_requested.connect(self.stop_generation)
        self.chat.attach_requested.connect(self.attach_file)
        self.chat.copy_requested.connect(self.copy_chat_to_clipboard)
        self.empty_team_panel = self._build_empty_team_panel()
        layout.addWidget(self.empty_team_panel, 1)
        layout.addWidget(self.chat, 1)
        self._update_empty_team_state()
        return panel

    def _build_empty_team_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("emptyTeamPanel")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.addStretch(1)

        content = QWidget()
        content.setMaximumWidth(620)
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        self.empty_team_title = QLabel()
        self.empty_team_title.setObjectName("pageTitle")
        self.empty_team_title.setAlignment(Qt.AlignCenter)
        self.empty_team_text = QLabel()
        self.empty_team_text.setObjectName("muted")
        self.empty_team_text.setAlignment(Qt.AlignCenter)
        self.empty_team_text.setWordWrap(True)
        self.empty_team_language = QComboBox()
        for label, value in (("Русский", "ru"), ("Українська", "uk"), ("English", "en")):
            self.empty_team_language.addItem(label, value)
        language = str(self.settings.get("interface_language", "ru"))
        self.empty_team_language.setCurrentIndex(max(0, self.empty_team_language.findData(language)))
        self.empty_team_language.currentIndexChanged.connect(self._change_first_run_language)

        actions = QHBoxLayout()
        self.connect_ai_button = QPushButton()
        self.connect_ai_button.setObjectName("smallAction")
        self.connect_ai_button.clicked.connect(self.show_director_console_preview)
        self.create_team_button = QPushButton()
        self.create_team_button.setObjectName("primaryButton")
        self.create_team_button.clicked.connect(self._start_first_team_creation)
        actions.addStretch(1)
        actions.addWidget(self.connect_ai_button)
        actions.addWidget(self.create_team_button)
        actions.addStretch(1)
        self.skip_onboarding_button = QPushButton()
        self.skip_onboarding_button.setObjectName("smallAction")
        self.skip_onboarding_button.clicked.connect(self._skip_onboarding)

        layout.addWidget(self.empty_team_title)
        layout.addWidget(self.empty_team_text)
        layout.addWidget(self.empty_team_language, 0, Qt.AlignHCenter)
        layout.addLayout(actions)
        layout.addWidget(self.skip_onboarding_button, 0, Qt.AlignHCenter)
        outer.addWidget(content, 0, Qt.AlignHCenter)
        outer.addStretch(2)
        self._translate_empty_team_panel(language)
        return panel

    def _translate_empty_team_panel(self, language: str) -> None:
        labels = {
            "ru": (
                "Добро пожаловать в Team2050",
                "У вас пока нет команды.",
                "Подключить ИИ",
                "Создать команду",
                "Пропустить",
            ),
            "uk": (
                "Ласкаво просимо до Team2050",
                "У вас поки немає команди.",
                "Підключити ШІ",
                "Створити команду",
                "Пропустити",
            ),
            "en": (
                "Welcome to Team2050",
                "You do not have a team yet.",
                "Connect AI",
                "Create team",
                "Skip",
            ),
        }
        title, text, connect, create, skip = labels.get(language, labels["ru"])
        self.empty_team_title.setText(title)
        self.empty_team_text.setText(text)
        self.connect_ai_button.setText(connect)
        self.create_team_button.setText(create)
        self.skip_onboarding_button.setText(skip)

    def _change_first_run_language(self) -> None:
        language = str(self.empty_team_language.currentData() or "ru")
        self.settings["interface_language"] = language
        self.universal_platform_service.identity_language = language
        self.settings_service.save(self.settings)
        self.chat.set_language(language)
        self._translate_empty_team_panel(language)

    def _skip_onboarding(self) -> None:
        self.settings["onboarding_skipped"] = True
        self.settings_service.save(self.settings)
        self._update_empty_team_state()

    def _update_empty_team_state(self) -> None:
        if not hasattr(self, "empty_team_panel") or not hasattr(self, "chat"):
            return
        has_team = bool(self.active_organization_id)
        skipped = bool(self.settings.get("onboarding_skipped", False))
        self.empty_team_panel.setVisible(not has_team and not skipped)
        self.chat.setVisible(has_team or skipped)

    def _start_first_team_creation(self) -> None:
        language = str(self.settings.get("interface_language", "ru"))
        templates = self.universal_platform_service.list_templates()
        if not templates:
            return
        labels = [catalog_label(language, template.name) for template in templates]
        titles = {
            "ru": ("Создать команду", "Выберите шаблон:"),
            "uk": ("Створити команду", "Оберіть шаблон:"),
            "en": ("Create team", "Choose a template:"),
        }
        title, prompt = titles.get(language, titles["ru"])
        selected, accepted = QInputDialog.getItem(self, title, prompt, labels, 0, False)
        if not accepted:
            return
        template = templates[labels.index(selected)]
        wizard = OrganizationActivationWizard(self.universal_platform_service, template, language, self)
        if wizard.exec() != OrganizationActivationWizard.Accepted or wizard.activation is None:
            return
        self.settings["onboarding_skipped"] = False
        self.settings_service.save(self.settings)
        self._activate_organization_live(wizard.activation.organization.organization_id)

    def _activate_organization_live(self, organization_id: str) -> None:
        self._refresh_organization_selector()
        index = self.organization_selector.findData(organization_id)
        if index >= 0:
            if self.active_organization_id != organization_id:
                self._switch_organization(index)
            else:
                self.organization_selector.setCurrentIndex(index)
        self._update_empty_team_state()

    def copy_chat_to_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = self.chat.transcript_text(selected_only=True)
        if not text:
            return
        application = QApplication.instance()
        if application is not None:
            application.clipboard().setText(text)

    def _build_inspector_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("inspectorPanel")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        profile = QFrame()
        profile.setObjectName("profileCard")
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(12, 12, 12, 12)
        profile_layout.addWidget(QLabel("Команда", objectName="pageTitle"))
        profile_layout.addWidget(QLabel("R+P", objectName="brandMark"))
        profile_layout.addWidget(QLabel("Сотрудники · назначенные AI-провайдеры\nКороткие ответы, общий план, разделение задач", objectName="muted"))
        profile_layout.addWidget(QLabel("●  оба доступны при авторизации", objectName="online"))
        about = QPushButton("Подробнее о команде  →")
        about.setObjectName("smallAction")
        about.clicked.connect(self.show_about_team)
        profile_layout.addWidget(about)
        layout.addWidget(profile)

        memory = QFrame()
        memory.setObjectName("card")
        memory_layout = QVBoxLayout(memory)
        memory_layout.setContentsMargins(12, 12, 12, 12)
        memory_layout.addWidget(QLabel("Память", objectName="sectionTitle"))
        self.memories = QListWidget()
        self.memories.setObjectName("conversationList")
        self.memories.setMinimumHeight(70)
        self.delete_memory_button = QPushButton("Забыть выбранное")
        self.delete_memory_button.setObjectName("smallAction")
        self.delete_memory_button.clicked.connect(self.delete_memory)
        memory_layout.addWidget(self.memories)
        memory_layout.addWidget(self.delete_memory_button)
        layout.addWidget(memory)
        workspace = QFrame()
        workspace.setObjectName("card")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(12, 12, 12, 12)
        workspace_layout.addWidget(QLabel("Рабочая папка", objectName="sectionTitle"))
        self.workspace_path_label = QLabel()
        self.workspace_path_label.setWordWrap(True)
        self.workspace_path_label.setObjectName("muted")
        workspace_layout.addWidget(self.workspace_path_label)
        workspace_buttons = QHBoxLayout()
        open_button = QPushButton("Открыть")
        open_button.setObjectName("smallAction")
        open_button.clicked.connect(self.open_workspace)
        change_button = QPushButton("Изменить")
        change_button.setObjectName("smallAction")
        change_button.clicked.connect(self.choose_workspace)
        workspace_buttons.addWidget(open_button)
        workspace_buttons.addWidget(change_button)
        workspace_layout.addLayout(workspace_buttons)
        layout.addWidget(workspace)
        layout.addStretch(1)
        scroll.setWidget(content)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)
        return panel

    def _first_start_checks(self) -> None:
        self.logger.info("app_started")
        try:
            identity_hash = self.identity_service.initialize_guard()
            self.identity_ok = True
            self.database.log_event("identity_loaded", identity_hash)
        except IdentityError as exc:
            self.identity_ok = False
            QMessageBox.critical(self, "Ошибка системного профиля", str(exc))
        # Provider version/authentication commands may wait on a CLI process.
        # They must not block construction of the interactive MainWindow.
        self._set_fast_provider_status()

    def _set_fast_provider_status(self) -> None:
        codex_available = self.codex_client.is_available()
        gemini_available = self.gemini_client.is_available() and self.gemini_client.has_api_key()
        self.codex_status_label.setText("Codex: доступен" if codex_available else "Codex: нет")
        self.gemini_status_label.setText("Gemini: доступен" if gemini_available else "Gemini: нет")
        self.auth_button.setText("Проверить вход" if codex_available else "Codex не найден")
        self.database.log_event(
            "provider_fast_status",
            f"codex_available={codex_available}; gemini_available={gemini_available}",
        )

    def refresh_codex_status(self) -> None:
        if not self.codex_client.is_available():
            self.codex_authorized = False
            self.codex_version = "не найден"
            self.codex_status_label.setText("Codex: нет")
            self.auth_button.setText("Codex не найден")
            self.refresh_gemini_status()
            return
        self.codex_version = self.codex_client.version()
        status = self.auth_service.status()
        self.codex_authorized = status.authorized
        state = "авторизован" if status.authorized else "не авторизован"
        self.codex_status_label.setText("Codex: OK" if status.authorized else "Codex: вход")
        self.auth_button.setText("Выйти" if status.authorized else "Войти")
        self.database.log_event("codex_status", f"{self.codex_version}; {status.message}; tools={bool(self.settings.get('allow_local_tools', False))}")
        self.refresh_gemini_status()

    def refresh_gemini_status(self) -> None:
        if not self.gemini_client.is_available():
            self.gemini_version = "не найден"
            self.gemini_status_label.setText("Gemini: нет")
            return
        self.gemini_version = self.gemini_client.version()
        key_state = "ключ задан" if self.gemini_client.has_api_key() else "нет ключа"
        self.gemini_status_label.setText("Gemini: OK" if self.gemini_client.has_api_key() else "Gemini: ключ")
        self.database.log_event("gemini_status", f"{self.gemini_version}; key={self.gemini_client.has_api_key()}")

    def load_conversation(self) -> None:
        self._refresh_organization_selector()
        self._refresh_chat_agents()
        self.chat.clear_messages()
        history_limit = max(1, int(self.settings.get("history_message_limit", 20)))
        for message in self.database.list_messages(self.conversation_id, limit=history_limit):
            if message.role != "system":
                self.chat.add_message(message.role, self._display_text_from_raw_response(message.content), message.id, message.created_at[11:16])
        self._update_empty_team_state()

    def _chat_agents(self) -> list[ChatAgent]:
        active_organization_id = self.active_organization_id
        if active_organization_id:
            organization = next(
                (row for row in self.database.list_organizations() if str(row["id"]) == active_organization_id),
                None,
            )
            if organization is None or str(organization["status"]).upper() != "ACTIVE":
                return []
            roster = list_chat_agents(self.database, organization_id=active_organization_id)
            return roster
        return list_chat_agents(self.database)

    def _refresh_organization_selector(self) -> None:
        selector = getattr(self, "organization_selector", None)
        if selector is None:
            return
        organizations = [row for row in self.database.list_organizations() if str(row["status"]).upper() != "ARCHIVED"]
        selector.blockSignals(True)
        selector.clear()
        if not organizations:
            selector.addItem("Общий чат", None)
        else:
            for row in organizations:
                selector.addItem(str(row["name"]), str(row["id"]))
        index = selector.findData(self.active_organization_id)
        selector.setCurrentIndex(index if index >= 0 else 0)
        selector.blockSignals(False)

    def _switch_organization(self, index: int) -> None:
        selector = getattr(self, "organization_selector", None)
        if selector is None:
            return
        organization_id = selector.itemData(index)
        if not organization_id or str(organization_id) == self.active_organization_id:
            return
        if self.worker is not None:
            self._refresh_organization_selector()
            QMessageBox.information(self, "Команда занята", "Дождитесь завершения текущего ответа перед сменой команды.")
            return
        organization_id = str(organization_id)
        organization = next(
            (row for row in self.database.list_organizations() if str(row["id"]) == organization_id),
            None,
        )
        if organization is None or str(organization["status"]).upper() != "ACTIVE":
            return
        self.database.set_active_organization(organization_id)
        self.active_organization_id = organization_id
        self.conversation_id = self.database.ensure_organization_conversation(organization_id, str(organization["name"]))
        self.universal_platform_service.conversation_id = self.conversation_id
        self.thread_service = ConversationThreadService(self.database, self.conversation_id)
        self.current_thread_id = self.thread_service.thread_id
        self.thread_question_service = ThreadQuestionService(self.database, self.conversation_id)
        self.work_context_service = WorkContextService(self.database, self.conversation_id, self.current_thread_id)
        self.conversation_mode = ConversationMode.SOCIAL
        self.current_task_id = None
        self.current_work_intent = UserIntent(IntentType.UNKNOWN, IntentType.UNKNOWN.value)
        self.current_work_reference = None
        self.current_execution_contract = None
        self.task_orchestrator.current_task_id = None
        self.chat.set_goal_status(False)
        self.load_conversation()
        self._refresh_work_context_strip()

    def _refresh_chat_agents(self) -> None:
        agents = self._chat_agents()
        labels = {agent.key: agent.display_name for agent in agents}
        avatars = {agent.key: agent.avatar_path for agent in agents if agent.avatar_path}
        user_avatar = str(self.settings.get("user_avatar_path") or "").strip()
        if user_avatar:
            avatars["user"] = user_avatar
        titles = {
            agent.key: role_label(str(self.settings.get("interface_language") or "ru"), agent.primary_role)
            for agent in agents
        }
        if hasattr(self, "chat"):
            self.chat.set_agent_labels(labels, avatars, titles)
        roster = getattr(self, "team_roster_layout", None)
        if roster is None:
            return
        while roster.count():
            item = roster.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not agents:
            empty = QLabel("В этой организации пока нет сотрудников. Добавьте первого сотрудника в разделе «Команда».")
            empty.setObjectName("emptyRoster")
            empty.setWordWrap(True)
            roster.addWidget(empty)
        for agent in agents:
            label = QLabel(f"●  {agent.display_name} · {agent.engine_name}")
            label.setObjectName("online")
            roster.addWidget(label)

    def reload_memories(self) -> None:
        self.memories.clear()
        memories = self.memory_service.list_memories()
        for memory in memories:
            item = QListWidgetItem(memory.content)
            item.setData(Qt.UserRole, memory.id)
            self.memories.addItem(item)
        if not memories:
            self.memories.addItem("Сохранённых воспоминаний пока нет")
            self.memories.item(0).setFlags(Qt.NoItemFlags)

    def remember_message(self, content: str) -> None:
        self.memory_service.remember(content)

    def delete_memory(self) -> None:
        item = self.memories.currentItem()
        if not item or item.data(Qt.UserRole) is None:
            return
        self.memory_service.delete_memory(int(item.data(Qt.UserRole)))
        self.reload_memories()

    def attach_file(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Прикрепить файл")
        if not source:
            return
        try:
            copied = self.workspace_service.copy_input_to_workspace(Path(source))
        except (OSError, ValueError, PathGuardError) as exc:
            QMessageBox.warning(self, "Файл не добавлен", str(exc))
            return
        self.database.log_event("file_imported", str(copied.relative_to(self.workspace_service.root)))
        self.chat.input.insertPlainText(f"[Файл скопирован в рабочую папку: {copied.name}] ")

    def _update_conversation_mode(self, text: str) -> None:
        options = self.chat.routing_options()
        requested = str(options.get("conversation_mode") or "").upper()
        if requested:
            try:
                self.conversation_mode = ConversationMode(requested)
            except ValueError:
                self.conversation_mode = infer_mode(text, self.conversation_mode)
        else:
            self.conversation_mode = infer_mode(text, self.conversation_mode)
        self._refresh_work_context_strip()

    def send_message(self, text: str) -> None:
        self._clear_dead_worker()
        if self.worker is not None:
            if is_stop_command(text):
                self._interrupt_with_user_message(text)
                self._clear_composer_input()
            elif self.cancellation_in_progress or self.interrupting_current_run:
                message_id = self._add_user_message(text)
                self.queued_user_message = (text, message_id)
                self.database.log_event("message_queued_during_cancellation", self.current_agent_key)
                self._clear_composer_input()
            else:
                self._add_live_guidance(text)
                self._clear_composer_input()
            return
        if is_stop_command(text):
            self._stop_autonomous(add_user_message=True, text=text)
            self._clear_composer_input()
            return
        if not self._identity_is_ready():
            return
        self._update_conversation_mode(text)
        autonomy = self._autonomy_from_text(text)
        if autonomy.enabled:
            self.conversation_mode = ConversationMode.WORK
            self._refresh_work_context_strip()
        if autonomy.enabled and autonomy.complete_on_goal and self.active_organization_id:
            self.chat.reset_stream()
            message_id = self._add_user_message(text)
            self._clear_composer_input()
            if self._start_director_goal(text, message_id):
                return
        agent_keys = self._route_agents(text, self._manual_routing())
        self.database.log_event("chat_route_selected", ",".join(agent_keys))
        if not agent_keys:
            message_id = self._add_user_message(text)
            self._clear_composer_input()
            self._record_last_routing_decision(message_id)
            self._persist_thread_from_last_decision(message_id, None, text)
            self._record_thread_question_from_last_decision(message_id, text)
            return
        agent_keys = self._autonomous_initial_agents(agent_keys, autonomy)
        if not self._agents_are_ready(agent_keys):
            return
        if self._any_agent_allows_local_tools(agent_keys):
            self.database.log_event("local_tools_enabled_for_request", ",".join(agent_keys))
        self.chat.reset_stream()
        message_id = self._add_user_message(text)
        self._clear_composer_input()
        if not self._prepare_work_context(text, message_id, agent_keys):
            return
        if self._prepare_generation_state(text, message_id, agent_keys, autonomy):
            self._record_last_routing_decision(message_id)
            self._persist_thread_from_last_decision(message_id, self.task_orchestrator.current_task_id, text)
            self._record_thread_question_from_last_decision(message_id, text)
            self._start_next_agent_run()
            QTimer.singleShot(1200, lambda mid=message_id: self._ensure_generation_started(mid))

    def _clear_composer_input(self) -> None:
        clear_input = getattr(getattr(self, "chat", None), "clear_input", None)
        if callable(clear_input):
            clear_input()

    def _start_user_message_from_existing(self, text: str, message_id: int | None = None) -> None:
        self._clear_dead_worker()
        if not self._identity_is_ready():
            return
        self._update_conversation_mode(text)
        autonomy = self._autonomy_from_text(text)
        if autonomy.enabled:
            self.conversation_mode = ConversationMode.WORK
            self._refresh_work_context_strip()
        agent_keys = self._route_agents(text, self._manual_routing())
        self.database.log_event("chat_route_selected", ",".join(agent_keys))
        if not agent_keys:
            self._record_last_routing_decision(message_id)
            self._persist_thread_from_last_decision(message_id, None, text)
            self._record_thread_question_from_last_decision(message_id, text)
            return
        agent_keys = self._autonomous_initial_agents(agent_keys, autonomy)
        if not self._agents_are_ready(agent_keys):
            return
        if self._any_agent_allows_local_tools(agent_keys):
            self.database.log_event("local_tools_enabled_for_request", ",".join(agent_keys))
        self.chat.reset_stream()
        if not self._prepare_work_context(text, message_id, agent_keys):
            return
        if self._prepare_generation_state(text, None, agent_keys, autonomy):
            self._record_last_routing_decision(message_id)
            self._persist_thread_from_last_decision(message_id, self.task_orchestrator.current_task_id, text)
            self._record_thread_question_from_last_decision(message_id, text)
            self._start_next_agent_run()
            QTimer.singleShot(1200, lambda mid=message_id: self._ensure_generation_started(mid))

    def _clear_dead_worker(self) -> None:
        if getattr(self, "active_workers", {}):
            return
        if self.worker is not None and not self.worker.isRunning():
            self.database.log_event("stale_worker_cleared", self.current_agent_key)
            self.worker = None
            self.cancellation_in_progress = False
            self.pending_agent_keys = []
            self.authorized_worker_keys = set()
            self._stop_response_latency_timers()
            self.chat.set_busy(False)

    def _prepare_generation_state(self, text: str, message_id: int | None, agent_keys: list[str], autonomy) -> bool:
        try:
            if self.conversation_mode == ConversationMode.WORK:
                context = self.work_context_service.get() if hasattr(self, "work_context_service") else None
                if context is not None and context.task_id:
                    self.task_orchestrator.current_task_id = context.task_id
                else:
                    task_id = self.task_orchestrator.start_user_task(text, message_id)
                    self.current_task_id = task_id
                    if hasattr(self, "work_context_service"):
                        self.work_context_service.bind_task(task_id, text[:160])
        except Exception as exc:
            self._report_generation_start_failure(exc)
            return False
        self.autonomous_active = autonomy.enabled
        self.autonomous_goal = autonomy.goal if autonomy.enabled else ""
        self.autonomous_complete_on_goal = autonomy.complete_on_goal
        self.autonomous_turn = 0
        self.autonomous_fingerprints = []
        self.autonomous_agent_keys = self._dedupe_agents(agent_keys) if autonomy.enabled else []
        self.exchange_turn = 0
        self.exchange_turn_limit = self._goal_turn_limit() if autonomy.enabled and autonomy.complete_on_goal else 8 if autonomy.enabled else len(agent_keys) or 1
        self.exchange_responded_agent_keys = set()
        self.exchange_fingerprints = []
        self.pending_contextual_handoffs = []
        self.live_guidance = []
        self.pending_agent_keys = list(agent_keys)
        self.authorized_worker_keys = set(agent_keys)
        self.pending_user_message = self.autonomous_goal or text
        self.last_peer_context = ""
        self.chat.set_goal_status(self.autonomous_active and self.autonomous_complete_on_goal, self.autonomous_goal, self.autonomous_turn)
        self._refresh_work_context_strip()
        return True

    def _start_director_goal(self, text: str, message_id: int | None) -> bool:
        if not self.active_organization_id:
            return False
        try:
            plan = self.director_service.create_plan(
                self.active_organization_id,
                self._autonomy_from_text(text).goal,
                owner_message_id=message_id,
                max_rework_attempts=int(self.settings.get("goal_rework_limit", 2)),
            )
        except ValueError as exc:
            self.database.log_event("director_goal_not_started", str(exc))
            return False
        self.active_director_plan_id = plan.plan_id
        self.autonomous_active = True
        self.autonomous_goal = plan.goal
        self.autonomous_complete_on_goal = True
        self.autonomous_turn = 0
        self.autonomous_fingerprints = []
        self.autonomous_agent_keys = []
        self.pending_agent_keys = []
        self.authorized_worker_keys = set()
        self.pending_user_message = plan.goal
        self.chat.set_goal_status(True, plan.goal, 0)
        self._record_last_routing_decision(message_id)
        self._persist_thread_from_last_decision(message_id, None, text)
        self._record_thread_question_from_last_decision(message_id, text)
        if plan.status == "NEEDS_STAFFING":
            self._finish_director_goal_with_notice(
                f"Цель не запущена: не хватает ролей {', '.join(plan.missing_roles)}. Добавьте исполнителя и независимого ревьюера."
            )
            return True
        if plan.status == "AWAITING_OWNER_APPROVAL":
            self._finish_director_goal_with_notice(
                "Цель требует отдельного подтверждения владельца из-за установки, удаления, оплаты или изменения прав."
            )
            return True
        self._schedule_director_action()
        return True

    def _schedule_director_action(self) -> None:
        plan_id = self.active_director_plan_id
        if not plan_id:
            return
        plan = self.director_service.get_plan(plan_id)
        if plan.status == "COMPLETED":
            self._finish_director_goal_with_notice(plan.summary or "Цель выполнена и прошла проверку.")
            return
        if plan.status == "BLOCKED":
            self._finish_director_goal_with_notice(f"Цель заблокирована: {plan.summary}")
            return
        action = self.director_service.next_action(plan_id)
        if action is None:
            if plan.status not in {"IN_PROGRESS", "READY"}:
                self._finish_director_goal_with_notice(f"Цель остановлена в состоянии: {plan.status}")
            return
        self.active_director_action = action
        self.task_orchestrator.current_task_id = action.task_id
        self.pending_agent_keys = [action.agent_key]
        self.authorized_worker_keys = {action.agent_key}
        self.pending_user_message = action.instruction
        self.autonomous_turn += 1
        self.chat.set_goal_status(True, plan.goal, self.autonomous_turn)
        self._start_next_agent_run()

    def _finish_director_goal_with_notice(self, text: str) -> None:
        plan_id = self.active_director_plan_id
        if plan_id:
            try:
                plan = self.director_service.get_plan(plan_id)
                if plan.status == "COMPLETED":
                    retrospective = self.learning_manager_service.retrospective_for_plan(plan_id)
                    for warning in retrospective.warnings:
                        self.database.log_event("learning_retrospective_warning", warning)
            except Exception:
                self.logger.exception("learning_retrospective_failed")
        if text:
            self.database.add_message(self.conversation_id, "system", text)
            self.chat.add_message("system", text)
        self.active_director_plan_id = None
        self.active_director_action = None
        self.pending_agent_keys = []
        self.pending_user_message = ""
        self.authorized_worker_keys = set()
        self._clear_goal_state()
        self.chat.set_busy(False)

    @staticmethod
    def _director_evidence(parsed_response: ParsedAgentResponse, registered_artifacts: list[str]) -> dict[str, object]:
        envelope = parsed_response.envelope if isinstance(parsed_response.envelope, dict) else {}
        return {
            "artifact_ids": list(registered_artifacts),
            "files_created": list(envelope.get("files_created") or []),
            "files_modified": list(envelope.get("files_modified") or []),
            "checks": list(envelope.get("checks") or []),
            "findings": list(envelope.get("findings") or []),
            "sources": list(envelope.get("sources") or []),
        }

    def _complete_director_action(
        self,
        worker: GenerateWorker | None,
        result,
        content: str,
        parsed_response: ParsedAgentResponse,
        message_id: int | None,
        registered_artifacts: list[str],
    ) -> None:
        action = self.active_director_action
        if action is None or worker is None or not worker.run_id:
            return
        envelope = parsed_response.envelope if isinstance(parsed_response.envelope, dict) else {}
        decision = str(envelope.get("action") or "") if action.assignment_type == "REVIEW" else ""
        findings = list(envelope.get("findings") or [])
        self.director_service.finish_assignment(
            action.assignment_id,
            ok=bool(result.ok),
            run_id=worker.run_id,
            message_id=message_id,
            summary=content or str(result.error or ""),
            evidence=self._director_evidence(parsed_response, registered_artifacts),
            review_decision=decision,
            findings=findings,
            error=str(result.error or ""),
        )
        self.active_director_action = None

    def _prepare_work_context(self, text: str, message_id: int | None, agent_keys: list[str]) -> bool:
        if self.conversation_mode != ConversationMode.WORK or not hasattr(self, "work_context_service"):
            return True
        names: dict[str, list[str]] = {}
        for agent in self._chat_agents():
            names[agent.key] = [agent.display_name, *agent.aliases]
        intent = self.intent_resolver.resolve(text, names)
        previous = self.work_context_service.get()
        reference = self.artifact_referent_resolver.resolve(text, previous)
        needs_artifact = intent.intent in {IntentType.FORMAT, IntentType.REVIEW, IntentType.MODIFY, IntentType.INSPECT}
        if needs_artifact and not reference.primary_artifact_id:
            message = "Не найден рабочий артефакт. Укажите файл или объект, который нужно обработать."
            self.database.add_message(self.conversation_id, "system", message, status="warning")
            self.chat.add_message("system", message)
            self.database.log_event("work_context_clarification_required", text[:240])
            return False
        self.current_work_intent = intent
        self.current_work_reference = reference
        self.work_context_service.apply_command(
            text=text,
            intent=intent,
            reference=reference,
            selected_agent_keys=agent_keys,
        )
        self.database.log_event(
            "work_context_command_resolved",
            f"intent={intent.intent.value}; artifacts={','.join(reference.artifact_ids) or 'none'}; agents={','.join(agent_keys)}",
        )
        self._refresh_work_context_strip()
        return True

    def _refresh_work_context_strip(self) -> None:
        label = getattr(self, "work_context_label", None)
        service = getattr(self, "work_context_service", None)
        if label is None or service is None:
            return
        if self.conversation_mode != ConversationMode.WORK:
            label.clear()
            label.setVisible(False)
            return
        context = service.get()
        if context is None:
            label.setVisible(False)
            label.setText("Текущая задача: нет активной задачи")
            return
        label.setVisible(True)
        owner = context.current_owner_agent_id or "не назначен"
        artifact = context.primary_artifact_id or "не выбран"
        label.setText(
            f"Текущая задача: {context.task_title or context.task_goal or 'без названия'}  ·  "
            f"Исполнитель: {owner}  ·  Объект: {artifact}  ·  "
            f"Операция: {context.current_operation}"
        )

    def show_work_context_diagnostic(self) -> None:
        service = getattr(self, "work_context_service", None)
        if service is None:
            QMessageBox.information(self, "Рабочий контекст", "Рабочий контекст пока не создан.")
            return
        context = service.get()
        if context is None:
            QMessageBox.information(self, "Рабочий контекст", "Активной задачи нет.")
            return
        handoffs = self.database.list_work_handoffs(self.conversation_id, limit=3)
        handoff_text = "\n".join(
            f"- {row['from_agent_id'] or 'пользователь'} -> {row['to_agent_id']}; {row['requested_operation']}; {row['status']}"
            for row in reversed(handoffs)
        ) or "- нет"
        contract = self.current_execution_contract
        text = "\n".join(
            ["ТЕКУЩАЯ ЗАДАЧА", *context.to_lines(), "", "ПОСЛЕДНИЕ ПЕРЕДАЧИ", handoff_text, "", "КОНТРАК", *(contract.to_lines() if contract else ["- активного контракта нет"])]
        )
        QMessageBox.information(self, "Рабочий контекст", text)

    def _goal_turn_limit(self) -> int:
        try:
            return max(20, int(self.settings.get("goal_turn_limit", 80)))
        except (TypeError, ValueError):
            return 80

    def _report_generation_start_failure(self, exc: Exception) -> None:
        detail = str(exc) or exc.__class__.__name__
        self.logger.exception("chat_generation_start_failed")
        try:
            self.database.log_event("chat_generation_start_failed", detail[:500])
        except Exception:
            self.logger.exception("chat_generation_start_failure_not_logged")
        self.worker = None
        self.pending_agent_keys = []
        self.authorized_worker_keys = set()
        self.pending_user_message = ""
        self.last_peer_context = ""
        self.pending_contextual_handoffs = []
        self._stop_response_latency_timers()
        self.chat.set_busy(False)
        self.chat.add_message("system", f"Не удалось запустить ответ сотрудников: {detail}")

    def _ensure_generation_started(self, message_id: int | None = None) -> None:
        if not self.pending_user_message:
            return
        if self.worker is not None and self.worker.isRunning():
            return
        if self.worker is not None:
            self.database.log_event("stale_worker_after_send_cleared", self.current_agent_key)
            self.worker = None
        if not self.pending_agent_keys:
            # The routing decision is authoritative. A delayed watchdog must
            # Never create a second decision and silently replace the router's
            # selected employee.
            self.database.log_event("generation_restart_skipped_without_authorized_worker", str(message_id))
            self.pending_user_message = ""
            self.chat.set_busy(False)
            return
        self.database.log_event(
            "generation_restart_after_silent_send",
            f"message_id={message_id}; agents={','.join(self.pending_agent_keys)}",
        )
        self._start_next_agent_run()

    def _manual_routing(self) -> ManualRouting:
        if not hasattr(self, "chat"):
            return ManualRouting()
        options = self.chat.routing_options()
        return ManualRouting(
            recipient_key=options.get("recipient_key") if isinstance(options.get("recipient_key"), str) else None,
            only_selected=bool(options.get("only_selected")),
            team_discussion=bool(options.get("team_discussion")),
            review_request=bool(options.get("review_request")),
            no_response=bool(options.get("no_response")),
        )

    def _autonomy_from_text(self, text: str) -> AutonomyRequest:
        request = parse_autonomy_request(text)
        if hasattr(self, "chat") and self.chat.goal_mode_requested() and text.strip():
            return AutonomyRequest(True, text.strip(), True)
        return request

    def _clear_goal_state(self) -> None:
        self.autonomous_active = False
        self.autonomous_goal = ""
        self.autonomous_complete_on_goal = False
        self.autonomous_turn = 0
        self.autonomous_fingerprints = []
        if hasattr(self, "chat"):
            self.chat.set_goal_status(False)

    def _route_agents(self, text: str, manual: ManualRouting | None = None) -> list[str]:
        agents = self._chat_agents()
        self.last_routing_text = text
        self.last_routing_owner_before = list(self.last_addressed_agent_keys)
        try:
            configured_agents = list_chat_agents(self.database, active_only=False, include_without_chat=True)
        except AttributeError:
            # Lightweight test doubles and pre-Phase-A integrations may expose
            # only the active roster. They still get the same routing policy.
            configured_agents = agents
        active_keys = {agent.key for agent in agents}
        blocked_agents = [agent for agent in configured_agents if agent.key not in active_keys or agent.lifecycle_state != "ACTIVE"]
        decision = self.team_router.decide(
            text,
            agents,
            active_owner=self.last_addressed_agent_keys,
            manual=manual,
            blocked_agents=blocked_agents,
            recently_answered=getattr(self, "exchange_responded_agent_keys", set()),
        )
        self.last_routing_decision = decision
        if decision.selected:
            self.last_addressed_agent_keys = list(decision.selected)
        self.database.log_event(
            "chat_route_decision",
            f"{decision.participation_mode}; selected={','.join(decision.selected)}; reason={decision.reason}",
        )
        return list(decision.selected)

    def _record_last_routing_decision(self, message_id: int | None) -> None:
        decision = self.last_routing_decision
        if decision is None:
            return
        try:
            self.database.record_routing_decision(
                message_id=message_id,
                thread_id=f"conversation-{self.conversation_id}",
                participation_mode=str(decision.participation_mode),
                explicit_recipients=decision.explicit_recipients,
                inferred_recipients=decision.inferred_recipients,
                selected_responders=decision.selected,
                excluded_responders=decision.excluded,
                interruption_policy=None,
                reason=decision.reason,
                router_version=decision.router_version,
                normalized_text=" ".join(getattr(self, "last_routing_text", "").lower().replace("ё", "е").split()),
                detected_recipient_tokens=decision.explicit_recipients,
                continuation_owner_before=getattr(self, "last_routing_owner_before", []),
                continuation_owner_after=list(decision.selected),
                fallback_used=False,
            )
        except Exception:
            self.logger.exception("routing_decision_not_recorded")

    def explain_last_routing_decision(self) -> str:
        decision = self.last_routing_decision
        if decision is None:
            return "Решение маршрутизатора ещё не создано."
        names = {agent.key: agent.display_name for agent in self._chat_agents()}
        selected = ", ".join(names.get(key, key) for key in decision.selected) or "никто"
        explicit = ", ".join(names.get(key, key) for key in decision.explicit_recipients) or "не найден"
        return (
            f"Фраза: {getattr(self, 'last_routing_text', '')}\n"
            f"Явный адресат: {explicit}\n"
            f"Выбранный сотрудник: {selected}\n"
            f"Режим: {decision.participation_mode}\n"
            f"Причина: {decision.reason}\n"
            "Резервный выбор сотрудника: не использован"
        )

    def show_routing_diagnostic(self) -> None:
        QMessageBox.information(self, "Диагностика маршрута", self.explain_last_routing_decision())

    def _persist_thread_from_last_decision(self, message_id: int | None, task_id: str | None, topic: str) -> None:
        decision = self.last_routing_decision
        if decision is None:
            return
        try:
            snapshot = self.thread_service.apply_routing_decision(
                decision,
                message_id=message_id,
                task_id=task_id,
                topic=topic,
            )
            owner_keys = snapshot.owner_keys
            if owner_keys:
                self.last_addressed_agent_keys = owner_keys
        except Exception:
            self.logger.exception("conversation_thread_not_updated")

    def _record_thread_question_from_last_decision(self, message_id: int | None, text: str) -> None:
        decision = self.last_routing_decision
        assigned = decision.selected if decision is not None else []
        try:
            self.thread_question_service.record_owner_question(
                message_id=message_id,
                text=text,
                assigned_agent_keys=assigned,
            )
        except Exception:
            self.logger.exception("thread_question_not_recorded")

    def _mark_thread_questions_answered(self, agent_key: str, message_id: int) -> None:
        try:
            self.thread_question_service.mark_answered_by_agent(agent_key=agent_key, answer_message_id=message_id)
        except Exception:
            self.logger.exception("thread_question_not_answered")

    @staticmethod
    def _looks_like_followup_to_last_assignee(text: str) -> bool:
        lowered = " ".join(text.lower().replace("ё", "е").split())
        followup_tokens = (
            "попробуй еще раз",
            "попробуйте еще раз",
            "еще раз",
            "повтори",
            "продолжай",
            "дальше",
            "давай дальше",
            "сделай это",
            "создай это",
            "исправь это",
            "так и сделай",
            "тогда сделай",
            "тогда создай",
        )
        return any(token in lowered for token in followup_tokens)

    def _gemini_is_ready(self) -> bool:
        self.refresh_gemini_status()
        if not self.gemini_client.is_available():
            QMessageBox.warning(self, "Gemini CLI не найден", "Установите Gemini CLI или проверьте PATH.")
            return False
        if not self.gemini_client.has_api_key():
            QMessageBox.warning(self, "Нет ключа Gemini", "Задайте переменную окружения GEMINI_API_KEY.")
            return False
        return True

    def _agents_are_ready(self, agent_keys: list[str]) -> bool:
        ready: list[str] = []
        for agent_key in list(agent_keys):
            route = self.agent_router.route(agent_key)
            if route.provider == "CODEX_CLI":
                if not self.codex_client.is_available():
                    self.refresh_codex_status()
                    if len(agent_keys) == 1:
                        QMessageBox.warning(self, "Codex CLI не найден", "Встроенный Codex CLI не найден в сборке.")
                        return False
                    self.chat.add_message("system", f"{agent_key} пропущен: Codex CLI недоступен.")
                    continue
                self.refresh_codex_status()
                if not self.codex_authorized:
                    if len(agent_keys) == 1:
                        QMessageBox.information(self, "Нужен вход", "Откройте настройки профиля и выполните вход через ChatGPT.")
                        return False
                    self.chat.add_message("system", f"{agent_key} пропущен: Codex CLI не авторизован.")
                    continue
                ready.append(agent_key)
            elif route.provider == "GEMINI_CLI":
                gemini_ready = self.gemini_client.is_available() and self.gemini_client.has_api_key()
                if not gemini_ready:
                    if len(agent_keys) == 1:
                        return self._gemini_is_ready()
                    self.chat.add_message("system", f"{agent_key} пропущен: Gemini CLI недоступен.")
                    continue
                ready.append(agent_key)
            else:
                if len(agent_keys) == 1:
                    QMessageBox.warning(self, "Сотрудник недоступен", f"{route.agent_id}: провайдер {route.provider} пока не подключен к чату.")
                    return False
                self.chat.add_message("system", f"{agent_key} пропущен: провайдер {route.provider} не готов.")
                continue
        agent_keys[:] = ready
        return bool(ready)

    def _add_user_message(self, text: str) -> int:
        message_id = self.database.add_message(self.conversation_id, "user", text)
        self.chat.add_message("user", text, message_id)
        self.chat_sound_service.play_send()
        return message_id

    def _add_live_guidance(self, text: str) -> None:
        self._add_user_message(text)
        self.live_guidance.append(text)
        self.live_guidance = self.live_guidance[-6:]
        guidance = "\n".join(f"- {item}" for item in self.live_guidance)
        if "ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ ПОЛЬЗОВАТЕЛЯ ВО ВРЕМЯ РАБОТЫ:" not in self.pending_user_message:
            self.pending_user_message = (
                f"{self.pending_user_message}\n\n"
                "ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ ПОЛЬЗОВАТЕЛЯ ВО ВРЕМЯ РАБОТЫ:\n"
                f"{guidance}"
            ).strip()
        else:
            self.pending_user_message = re.sub(
                r"ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ ПОЛЬЗОВАТЕЛЯ ВО ВРЕМЯ РАБОТЫ:\n(?:- .+\n?)*",
                f"ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ ПОЛЬЗОВАТЕЛЯ ВО ВРЕМЯ РАБОТЫ:\n{guidance}",
                self.pending_user_message,
            )
        self.database.log_event("live_user_guidance_added", text[:240])

    def _ordered_autonomous_agents(self, agent_keys: list[str]) -> list[str]:
        if len(agent_keys) > 1:
            return self._dedupe_agents(agent_keys)
        agents = [agent.key for agent in self._chat_agents()]
        if not agents:
            return self._dedupe_agents(agent_keys)
        if agent_keys and agent_keys[0] in agents:
            rest = [agent for agent in agents if agent != agent_keys[0]]
            return [agent_keys[0], *rest[:1]]
        return agents[:2]

    def _autonomous_initial_agents(self, agent_keys: list[str], autonomy) -> list[str]:
        agent_keys = self._dedupe_agents(agent_keys)
        if not autonomy.enabled:
            return agent_keys
        decision = self.last_routing_decision
        if decision is not None and decision.explicit_recipients and len(agent_keys) == 1:
            return agent_keys
        return self._ordered_autonomous_agents(agent_keys)

    @staticmethod
    def _dedupe_agents(agent_keys: list[str]) -> list[str]:
        result = []
        for key in agent_keys:
            if key not in result:
                result.append(key)
        return result

    def _interrupt_with_user_message(self, text: str) -> None:
        if self.active_director_plan_id and is_stop_command(text):
            self.director_service.cancel_plan(self.active_director_plan_id, "stopped_by_owner")
            self.active_director_plan_id = None
            self.active_director_action = None
        self._clear_goal_state()
        self.exchange_turn = 0
        self.exchange_turn_limit = 0
        self.exchange_responded_agent_keys = set()
        self.exchange_fingerprints = []
        self.live_guidance = []
        self.pending_agent_keys = []
        self.pending_user_message = ""
        self.last_peer_context = ""
        self.pending_contextual_handoffs = []
        self.chat.discard_stream()
        if is_stop_command(text):
            self.queued_user_message = None
            self._add_user_message(text)
        else:
            message_id = self._add_user_message(text)
            self.queued_user_message = (text, message_id)
        self.interrupting_current_run = True
        self.cancellation_in_progress = True
        workers = list(self.active_workers.values())
        if self.worker is not None and self.worker not in workers:
            workers.append(self.worker)
        for worker in workers:
            worker.cancel()
        self.database.log_event("agent_interrupted_by_user", self.current_agent_key)

    def _stop_autonomous(self, add_user_message: bool = False, text: str = "стоп") -> None:
        if add_user_message:
            self._add_user_message(text)
        if self.active_director_plan_id:
            self.director_service.cancel_plan(self.active_director_plan_id, "stopped_by_owner")
            self.active_director_plan_id = None
            self.active_director_action = None
        self._clear_goal_state()
        self.exchange_turn = 0
        self.exchange_turn_limit = 0
        self.exchange_responded_agent_keys = set()
        self.exchange_fingerprints = []
        self.live_guidance = []
        self.pending_agent_keys = []
        self.pending_user_message = ""
        self.last_peer_context = ""
        self.pending_contextual_handoffs = []
        self.queued_user_message = None
        self.interrupting_current_run = False
        self.cancellation_in_progress = False
        self.chat.set_busy(False)
        self.database.log_event("autonomous_conversation_stopped", None)

    @staticmethod
    def _signals_autonomous_done(content: str) -> bool:
        return bool(re.search(r"\bAUTO_DONE\b", content))

    @staticmethod
    def _strip_autonomous_done(content: str) -> str:
        return re.sub(r"\bAUTO_DONE\b", "", content).strip()

    def _is_repeated_autonomous_content(self, content: str) -> bool:
        signature = self._content_signature(content)
        if len(signature) < 24:
            return False
        repeated = any(self._signature_similarity(signature, previous) >= 0.70 for previous in self.autonomous_fingerprints[-6:])
        if not repeated:
            self.autonomous_fingerprints.append(signature)
            self.autonomous_fingerprints = self.autonomous_fingerprints[-8:]
        return repeated

    def _is_repeated_exchange_content(self, content: str) -> bool:
        signature = self._content_signature(content)
        if len(signature) < 24:
            return False
        repeated = any(self._signature_similarity(signature, previous) >= 0.62 for previous in self.exchange_fingerprints[-8:])
        if not repeated:
            self.exchange_fingerprints.append(signature)
            self.exchange_fingerprints = self.exchange_fingerprints[-10:]
        return repeated

    def _is_recent_duplicate_message(self, role: str, content: str) -> bool:
        signature = self._content_signature(content)
        if len(signature) < 24:
            return False
        recent = self.database.list_messages(self.conversation_id, limit=12)
        normalized = re.sub(r"\W+", "", content.lower())
        for message in recent:
            if message.role != role:
                continue
            previous_normalized = re.sub(r"\W+", "", message.content.lower())
            if (
                len(normalized) >= 60
                and len(previous_normalized) >= 60
                and (normalized in previous_normalized or previous_normalized in normalized)
            ) or self._signature_similarity(signature, self._content_signature(message.content)) >= 0.72:
                return True
        return False

    @staticmethod
    def _content_signature(content: str) -> str:
        words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", content.lower())
        stop_words = {
            "принял",
            "принята",
            "васян",
            "готов",
            "понял",
            "по",
            "задача",
            "работаем",
        }
        useful = [word for word in words if word not in stop_words]
        return " ".join(useful[:80])

    @staticmethod
    def _signature_similarity(left: str, right: str) -> float:
        left_words = set(left.split())
        right_words = set(right.split())
        if not left_words or not right_words:
            return 0.0
        return len(left_words & right_words) / len(left_words | right_words)

    def _start_next_agent_run(self) -> None:
        if not hasattr(self, "active_workers"):
            self.active_workers = {}
        if self.active_workers:
            return
        if self._should_run_team_in_parallel():
            agent_keys = list(self.pending_agent_keys)
            self.pending_agent_keys = []
            self.chat.send_button.setVisible(False)
            self.chat.stop_button.setVisible(True)
            for agent_key in agent_keys:
                self._launch_agent_run(agent_key, parallel=True)
            return
        if not self.pending_agent_keys:
            if self.autonomous_active:
                turn_limit = self.exchange_turn_limit or (self._goal_turn_limit() if self.autonomous_complete_on_goal else 8)
                if self.autonomous_turn >= turn_limit:
                    goal = self.autonomous_goal
                    self._clear_goal_state()
                    self.pending_user_message = ""
                    self.last_peer_context = ""
                    self.pending_contextual_handoffs = []
                    self.chat.set_busy(False)
                    self.database.log_event("autonomous_conversation_turn_limit", goal[:500] if goal else None)
                    if goal:
                        self.chat.add_message(
                            "system",
                            f"Цель остановлена защитным лимитом ({turn_limit} ходов), чтобы не уйти в бесконечный цикл. Цель не отмечена выполненной: {goal}",
                        )
                    return
                active_keys = [agent.key for agent in self._chat_agents()]
                cycle_keys = [key for key in getattr(self, "autonomous_agent_keys", []) if key in active_keys] or active_keys
                if not cycle_keys:
                    self.pending_user_message = ""
                    self.chat.set_busy(False)
                    self.database.log_event("autonomous_cycle_skipped_without_active_agents", None)
                    return
                try:
                    current_index = cycle_keys.index(self.current_agent_key)
                    next_agent = cycle_keys[(current_index + 1) % len(cycle_keys)]
                except ValueError:
                    next_agent = cycle_keys[0]
                self.pending_agent_keys = [next_agent]
                self.authorized_worker_keys.add(next_agent)
                QTimer.singleShot(250, self._start_next_agent_run)
                return
            self.worker = None
            self.pending_user_message = ""
            self.last_peer_context = ""
            self.pending_contextual_handoffs = []
            self.chat.set_busy(False)
            self.refresh_codex_status()
            return
        agent_key = self.pending_agent_keys.pop(0)
        self._launch_agent_run(agent_key, parallel=False)

    def _should_run_team_in_parallel(self) -> bool:
        if self.autonomous_active or len(self.pending_agent_keys) < 2:
            return False
        decision = self.last_routing_decision
        if decision is None:
            return False
        mode = getattr(decision.participation_mode, "value", str(decision.participation_mode))
        return mode in {"TEAM_CALL", "GENERAL_TEAM_PING", "MULTI_DIRECT"}

    def _launch_agent_run(self, agent_key: str, parallel: bool = False) -> None:
        if not self._worker_agent_is_authorized(agent_key):
            self.database.log_event(
                "worker_selection_rejected",
                f"{agent_key}; selected={','.join(sorted(self.authorized_worker_keys))}",
            )
            self.pending_agent_keys = []
            self.pending_user_message = ""
            if not parallel:
                self.chat.set_busy(False)
            return
        if not self.autonomous_active:
            if self.exchange_turn >= self.exchange_turn_limit or agent_key in self.exchange_responded_agent_keys:
                self.database.log_event("exchange_turn_suppressed", agent_key)
                self.pending_agent_keys = []
                self.worker = None
                self.pending_user_message = ""
                self.last_peer_context = ""
                self.pending_contextual_handoffs = []
                if not parallel:
                    self.chat.set_busy(False)
                self.refresh_codex_status()
                return
        self.current_agent_key = agent_key
        if self.autonomous_active:
            self.autonomous_turn += 1
            self.chat.set_goal_status(self.autonomous_complete_on_goal, self.autonomous_goal, self.autonomous_turn)
        self.exchange_turn += 1
        allow_tools = self._allow_local_tools_for_agent(agent_key)
        try:
            run_handle = self.task_orchestrator.start_run(agent_key)
        except Exception as exc:
            self._report_generation_start_failure(exc)
            return
        if getattr(self, "active_director_action", None) is not None:
            try:
                if self.active_director_action.agent_key != agent_key:
                    raise ValueError("director_assignment_agent_mismatch")
                self.director_service.start_assignment(self.active_director_action.assignment_id, run_handle.run_id)
            except Exception as exc:
                self._report_generation_start_failure(exc)
                return
        client = self._client_for_agent(agent_key)
        context = self.work_context_service.get() if hasattr(self, "work_context_service") else None
        contract = None
        if context is not None and hasattr(self, "work_context_service"):
            try:
                contract = self.work_context_service.create_contract(
                    context=context,
                    intent=getattr(self, "current_work_intent", UserIntent(IntentType.UNKNOWN, IntentType.UNKNOWN.value)),
                    user_instruction=self.pending_user_message,
                    agent_id=run_handle.agent_id,
                    role=run_handle.role,
                    run_id=run_handle.run_id,
                    allowed_tools=["READ_WORKSPACE", "WRITE_WORKSPACE", "CREATE_DOCUMENTS", "RUN_COMMANDS"] if allow_tools else [],
                )
                self.current_execution_contract = contract
            except Exception:
                self.logger.exception("execution_contract_not_created")
        if parallel:
            self.chat.start_agent_typing(agent_key)
        else:
            self.chat.reset_stream()
            self.chat.set_stream_role(agent_key)
            self.chat.set_busy(True, self.pending_user_message)
        builder = PromptBuilder(
            self.paths.system_prompt_path,
            self.identity_service,
            self.paths.timeline_path,
            self.database,
            int(self.settings.get("history_message_limit", 20)),
            self.skill_service,
            self.knowledge_service,
            self.standards_service,
        )
        worker = GenerateWorker(
            builder,
            client,
            self.conversation_id,
            self.pending_user_message,
            allow_tools,
            agent_key=agent_key,
            peer_context=self.last_peer_context,
            autonomous_goal=self.autonomous_goal,
            autonomous_turn=self.autonomous_turn,
            complete_on_goal=self.autonomous_complete_on_goal,
            run_id=run_handle.run_id,
            task_id=run_handle.task_id,
            participation_mode=str(self.last_routing_decision.participation_mode) if self.last_routing_decision else "DIRECT",
            thread_context_lines=self.thread_service.prompt_lines(),
            active_work_context_lines=context.to_lines() if context is not None else [],
            execution_contract_lines=contract.to_lines() if contract is not None else [],
            organization_id=getattr(self, "active_organization_id", None),
            conversation_mode=getattr(self, "conversation_mode", ConversationMode.SOCIAL).value,
        )
        if parallel:
            worker.status_received.connect(lambda status, key=agent_key: self.chat.set_agent_activity_status(key, status))
            worker.run_status_received.connect(lambda status, run_id=run_handle.run_id: self._record_run_status(run_id, status))
            worker.finished_with_result.connect(
                lambda result, key=agent_key, current_worker=worker: self._generation_finished_parallel(key, current_worker, result)
            )
            self.active_workers[agent_key] = worker
        else:
            self.worker = worker
            append_delta = getattr(self.chat, "append_agent_delta", None)
            if append_delta is None:
                # Keep compatibility with older chat adapters while all new
                # providers use the agent-neutral method name.
                append_delta = self.chat.append_roman_delta
            worker.delta_received.connect(append_delta)
            worker.status_received.connect(self.chat.set_activity_status)
            worker.run_status_received.connect(lambda status, run_id=run_handle.run_id: self._record_run_status(run_id, status))
            worker.finished_with_result.connect(self._generation_finished)
        worker.start()
        self._mark_contextual_handoff_started(agent_key, run_handle.run_id)
        if not parallel:
            self._start_response_latency_timers(agent_key)

    def _generation_finished_parallel(self, agent_key: str, worker: GenerateWorker, result) -> None:
        self.active_workers.pop(agent_key, None)
        self.chat.stop_agent_typing(agent_key)
        raw_response = result.content if result.ok else (result.error or "")
        if worker.run_id is not None:
            self.task_orchestrator.finish_run(worker.run_id, result, raw_response)
        self.exchange_responded_agent_keys.add(agent_key)
        if result.ok:
            parsed_response = parse_agent_response(result.content)
            content = ResponseCleaner.clean(self._display_text_from_parsed_response(parsed_response))
            if not content:
                content = ResponseCleaner.clean(self._display_text_from_raw_response(result.content))
            if content and not self._is_recent_duplicate_message(agent_key, content):
                message_id = self.database.add_message(self.conversation_id, agent_key, content)
                self.chat.add_message(agent_key, content, message_id)
                self.chat_sound_service.play_receive()
                self._mark_thread_questions_answered(agent_key, message_id)
                claim_validation = self.claim_validator.validate(content, parsed_response.envelope)
                self._show_claim_warning_if_needed(self.conversation_id, claim_validation.warning)
                registered_artifacts = self._import_structured_artifacts(worker, parsed_response, agent_key)
                self._record_work_result(worker, agent_key, content, parsed_response, message_id, registered_artifacts)
                self._import_structured_findings(worker, parsed_response, agent_key)
                self._import_structured_usage(worker, parsed_response, agent_key)
                self._record_learning_evidence(worker, content)
                if not claim_validation.blocks_skill_update:
                    self.skill_service.learn_from_exchange(agent_key, self.pending_user_message, content)
                    self.skill_service.improve_from_context(agent_key, self.autonomous_goal or self.pending_user_message, content)
        elif result.cancelled:
            # A deliberate stop is not a provider failure and should not add noise to the chat.
            pass
        else:
            detail = result.error or "Провайдер не вернул ответ"
            content = f"Провайдер сотрудника не ответил: {detail}"
            self.database.log_event("provider_runtime_error", f"{agent_key}: {detail}"[:1000])
            self.database.add_message(self.conversation_id, "system", content, status="provider_error")
            self.chat.add_message("system", content)
        if self.active_workers:
            self.worker = next(iter(self.active_workers.values()))
            return
        self.worker = None
        self.pending_user_message = ""
        self.last_peer_context = ""
        self.pending_contextual_handoffs = []
        self._stop_response_latency_timers()
        self.chat.set_busy(False)
        self.refresh_codex_status()

    def _allow_local_tools_for_agent(self, agent_key: str) -> bool:
        return agent_can_use_local_tools(
            self.database,
            agent_id_from_key(agent_key),
            bool(self.settings.get("allow_local_tools", False)),
        )

    def _record_run_status(self, run_id: str, status: str) -> None:
        try:
            self.database.update_agent_run_status(run_id, status)
            self.database.log_event("agent_run_status", f"{run_id}; {status}")
        except Exception:
            self.logger.exception("agent_run_status_not_recorded")

    def _any_agent_allows_local_tools(self, agent_keys: list[str]) -> bool:
        return any(self._allow_local_tools_for_agent(agent_key) for agent_key in agent_keys)

    def _start_response_latency_timers(self, agent_key: str) -> None:
        self._stop_response_latency_timers()
        policy = ResponseLatencyPolicy.from_settings(self.settings)
        self.latency_soft_timer.start(policy.soft_warning_seconds * 1000)
        self.latency_extended_timer.start(policy.extended_warning_seconds * 1000)
        if policy.timeout_enabled:
            self.latency_timeout_timer.start(policy.timeout_seconds * 1000)
        self.database.log_event(
            "response_latency_tracking_started",
            f"{agent_key}; soft={policy.soft_warning_seconds}; extended={policy.extended_warning_seconds}; timeout={policy.timeout_seconds}",
        )

    def _stop_response_latency_timers(self) -> None:
        for timer in (self.latency_soft_timer, self.latency_extended_timer, self.latency_timeout_timer):
            if timer.isActive():
                timer.stop()

    def _show_response_latency_warning(self, stage: str) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        agent_key = self.worker.agent_key
        chat_agent = get_chat_agent(self.database, agent_key)
        name = chat_agent.display_name if chat_agent is not None else "Сотрудник"
        if stage == "soft":
            status = f"{name} отвечает дольше обычного"
            event = "response_latency_soft_warning"
        else:
            status = f"{name} всё ещё работает: можно подождать, написать уточнение или нажать \"Остановить\""
            event = "response_latency_extended_warning"
        self.chat.set_activity_status(status)
        self.database.log_event(event, agent_key)

    def _response_latency_timeout(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        agent_key = self.worker.agent_key
        self.database.log_event("response_latency_timeout_cancelled", agent_key)
        self.chat.set_activity_status("лимит ожидания истёк, останавливаю ответ")
        self.worker.cancel()

    def _client_for_agent(self, agent_key: str):
        route = self.agent_router.route(agent_key)
        if route.provider == "GEMINI_CLI":
            return self.gemini_client
        return self.codex_client

    def _schedule_contextual_next_turn(self, author: str, content: str) -> None:
        if self.autonomous_active or getattr(self, "conversation_mode", ConversationMode.WORK) != ConversationMode.WORK:
            return
        if self.exchange_turn >= self.exchange_turn_limit:
            return
        next_agent = self._contextual_handoff_target(author, content)
        if next_agent is None or next_agent in self.exchange_responded_agent_keys:
            return
        if next_agent not in self.pending_agent_keys:
            self.pending_agent_keys.append(next_agent)
            if not hasattr(self, "authorized_worker_keys"):
                self.authorized_worker_keys = set()
            self.authorized_worker_keys.add(next_agent)
            handoff = (author, next_agent)
            if not hasattr(self, "pending_contextual_handoffs"):
                self.pending_contextual_handoffs = []
            if handoff not in self.pending_contextual_handoffs:
                self.pending_contextual_handoffs.append(handoff)
            self.database.log_event("contextual_handoff_scheduled", f"{author}->{next_agent}")
        # A handoff is a bounded workflow edge, not a reason to turn a normal
        # direct request into an autonomous conversation.

    def _contextual_handoff_target(self, author: str, content: str) -> str | None:
        if getattr(self, "conversation_mode", ConversationMode.WORK) != ConversationMode.WORK or not has_handoff_intent(content):
            return None
        agents = self._chat_agents()
        active_keys = {agent.key for agent in agents}
        mentioned = [key for key in self.team_router._mentioned_agents(content, agents) if key != author]
        if mentioned:
            return mentioned[0]
        return None

    def _mark_contextual_handoff_started(self, agent_key: str, run_id: str) -> None:
        if not hasattr(self, "pending_contextual_handoffs"):
            self.pending_contextual_handoffs = []
        for index, (author, target) in enumerate(list(self.pending_contextual_handoffs)):
            if target != agent_key:
                continue
            self.pending_contextual_handoffs.pop(index)
            self.database.log_event("contextual_handoff_started", f"{author}->{target}; run={run_id}")
            return

    def _worker_agent_is_authorized(self, agent_key: str) -> bool:
        if self.autonomous_active:
            return agent_key in {agent.key for agent in self._chat_agents()}
        return agent_key in getattr(self, "authorized_worker_keys", set())

    def _identity_is_ready(self) -> bool:
        if not self.identity_ok:
            QMessageBox.warning(self, "Системный профиль недоступен", "Чат заблокирован до восстановления системного профиля.")
            return False
        try:
            if self.identity_service.check_for_change():
                self.identity_ok = False
                QMessageBox.warning(self, "Системный профиль изменён", "Восстановите системный профиль и перезапустите приложение.")
                return False
        except IdentityError as exc:
            self.identity_ok = False
            QMessageBox.warning(self, "Ошибка системного профиля", str(exc))
            return False
        return True

    def _generation_finished(self, result) -> None:
        worker = self.worker
        conversation_id = worker.conversation_id if worker is not None else self.conversation_id
        agent_key = worker.agent_key if worker is not None else self.current_agent_key
        chat_agent = get_chat_agent(self.database, agent_key)
        agent_name = chat_agent.display_name if chat_agent is not None else "Сотрудник"
        if worker is not None and worker.run_id is not None:
            raw_response = result.content if result.ok else (result.error or "")
            self.task_orchestrator.finish_run(worker.run_id, result, raw_response)
        self._stop_response_latency_timers()
        self.chat.set_busy(False)
        self.chat.clear_activity_status()
        director_content = ""
        director_message_id: int | None = None
        director_artifacts: list[str] = []
        director_parsed_response = parse_agent_response(result.content if result.ok else "")
        if self.interrupting_current_run:
            self.worker = None
            self.interrupting_current_run = False
            self.cancellation_in_progress = False
            queued = self.queued_user_message
            self.queued_user_message = None
            if queued is not None and not is_stop_command(queued[0]):
                self._start_user_message_from_existing(queued[0], queued[1])
            else:
                self.refresh_codex_status()
            return
        if result.ok:
            self.exchange_responded_agent_keys.add(agent_key)
            parsed_response = parse_agent_response(result.content)
            content = ResponseCleaner.clean(self._display_text_from_parsed_response(parsed_response))
            done_marker_seen = self._signals_autonomous_done(content)
            autonomous_done = self.autonomous_active and done_marker_seen
            if done_marker_seen:
                content = ResponseCleaner.clean(self._strip_autonomous_done(content))
            if self.autonomous_active and not autonomous_done and self._is_repeated_autonomous_content(content):
                self.chat.discard_stream()
                if self.autonomous_complete_on_goal:
                    self.database.log_event("goal_repeated_content_suppressed", agent_key)
                    self.last_peer_context = "Предыдущий ход был повтором и отброшен. Продолжай цель новым действием, проверкой или результатом."
                else:
                    self._clear_goal_state()
                    self.pending_agent_keys = []
                    self.database.log_event("autonomous_conversation_repetition_stopped", None)
                content = ""
            if content and self._is_repeated_exchange_content(content):
                self.chat.discard_stream()
                if self.autonomous_active:
                    if self.autonomous_complete_on_goal:
                        self.database.log_event("goal_exchange_repeated_content_suppressed", agent_key)
                        self.last_peer_context = "Ответ повторял уже сказанное и отброшен. Следующий ход должен дать новый факт, файл, проверку или завершить цель через AUTO_DONE."
                    else:
                        self._clear_goal_state()
                        self.pending_agent_keys = []
                else:
                    self.pending_agent_keys = []
                self.database.log_event("exchange_repeated_content_suppressed", agent_key)
                content = ""
            if content:
                parts = ResponseSplitter.split(content, agent_key, self._response_speaker_aliases())
                if len(parts) == 1 and parts[0].role == agent_key:
                    final_content = parts[0].content
                    if self._is_recent_duplicate_message(agent_key, final_content):
                        self.chat.discard_stream()
                        if self.autonomous_active and self.autonomous_complete_on_goal:
                            self.last_peer_context = "Дубликат сообщения отброшен. Продолжай цель новым действием или заверши ее только при реальном результате."
                        else:
                            self.pending_agent_keys = []
                            self._clear_goal_state()
                        self.database.log_event("duplicate_agent_message_suppressed", agent_key)
                    else:
                        message_id = self.database.add_message(conversation_id, agent_key, final_content)
                        self.chat.finish_agent_response(final_content)
                        self.chat.set_stream_message_id(message_id, final_content)
                        self.chat_sound_service.play_receive()
                        self._mark_thread_questions_answered(agent_key, message_id)
                        claim_validation = self.claim_validator.validate(final_content, parsed_response.envelope)
                        self._show_claim_warning_if_needed(conversation_id, claim_validation.warning)
                        registered_artifacts = self._import_structured_artifacts(worker, parsed_response, agent_key)
                        director_content = final_content
                        director_message_id = message_id
                        director_artifacts = registered_artifacts
                        director_parsed_response = parsed_response
                        self._record_work_result(worker, agent_key, final_content, parsed_response, message_id, registered_artifacts)
                        self._import_structured_findings(worker, parsed_response, agent_key)
                        self._import_structured_usage(worker, parsed_response, agent_key)
                        self._record_learning_evidence(worker, final_content)
                        if not claim_validation.blocks_skill_update:
                            self.skill_service.learn_from_exchange(agent_key, self.pending_user_message, final_content)
                            self.skill_service.improve_from_context(agent_key, self.autonomous_goal or self.pending_user_message, final_content)
                        self.last_peer_context = final_content
                        self._schedule_contextual_next_turn(agent_key, final_content)
                else:
                    self.chat.discard_stream()
                    own_parts = [ResponseCleaner.clean(part.content) for part in parts if part.role == agent_key]
                    foreign_roles = sorted({part.role for part in parts if part.role != agent_key})
                    if foreign_roles:
                        self.database.log_event("impersonated_response_suppressed", f"{agent_key} wrote for {','.join(foreign_roles)}")
                        self._show_claim_warning_if_needed(
                            conversation_id,
                            f"{agent_name} попытался написать за другого сотрудника. Чужие реплики не приняты.",
                        )
                    clean_part = ResponseCleaner.clean("\n\n".join(part for part in own_parts if part))
                    if clean_part and not self._is_recent_duplicate_message(agent_key, clean_part):
                        message_id = self.database.add_message(conversation_id, agent_key, clean_part)
                        self.chat.add_message(agent_key, clean_part, message_id)
                        self.chat_sound_service.play_receive()
                        self._mark_thread_questions_answered(agent_key, message_id)
                        claim_validation = self.claim_validator.validate(clean_part, parsed_response.envelope)
                        self._show_claim_warning_if_needed(conversation_id, claim_validation.warning)
                        registered_artifacts = self._import_structured_artifacts(worker, parsed_response, agent_key)
                        director_content = clean_part
                        director_message_id = message_id
                        director_artifacts = registered_artifacts
                        director_parsed_response = parsed_response
                        self._record_work_result(worker, agent_key, clean_part, parsed_response, message_id, registered_artifacts)
                        self._import_structured_findings(worker, parsed_response, agent_key)
                        self._import_structured_usage(worker, parsed_response, agent_key)
                        self._record_learning_evidence(worker, clean_part)
                        if not claim_validation.blocks_skill_update:
                            self.skill_service.learn_from_exchange(agent_key, self.pending_user_message, clean_part)
                            self.skill_service.improve_from_context(agent_key, self.autonomous_goal or self.pending_user_message, clean_part)
                        self.exchange_responded_agent_keys.add(agent_key)
                        self._schedule_contextual_next_turn(agent_key, clean_part)
                        self.last_peer_context = clean_part
                    else:
                        self.database.log_event("impersonated_or_duplicate_response_discarded", agent_key)
                    self.current_agent_key = agent_key
                    while self.pending_agent_keys and self.pending_agent_keys[0] == agent_key:
                        self.pending_agent_keys.pop(0)
            else:
                self.chat.discard_stream()
            if autonomous_done:
                self._clear_goal_state()
                self.pending_agent_keys = []
        else:
            detail = result.error or "Провайдер не вернул ответ"
            if result.cancelled:
                content = "Ответ остановлен пользователем."
                self.database.add_message(conversation_id, "system", content, status="cancelled")
            else:
                content = f"Провайдер сотрудника не ответил: {detail}"
                self.database.log_event("provider_runtime_error", f"{agent_key}: {detail}"[:1000])
                self.database.add_message(conversation_id, "system", content, status="provider_error")
            self.chat.add_message("system", content)
        if getattr(self, "active_director_action", None) is not None:
            try:
                self._complete_director_action(
                    worker,
                    result,
                    director_content,
                    director_parsed_response,
                    director_message_id,
                    director_artifacts,
                )
            except Exception:
                self.logger.exception("director_action_completion_failed")
                if self.active_director_plan_id:
                    self.director_service.cancel_plan(self.active_director_plan_id, "workflow_completion_error")
                self._finish_director_goal_with_notice("Цель остановлена из-за ошибки обработки результата. Подробности записаны в журнал.")
        self.worker = None
        self.cancellation_in_progress = False
        if getattr(self, "active_director_plan_id", None):
            QTimer.singleShot(250, self._schedule_director_action)
            return
        if not result.ok and self.conversation_id == conversation_id:
            self._clear_goal_state()
            self.pending_agent_keys = []
            self.pending_user_message = ""
            self.last_peer_context = ""
            self.pending_contextual_handoffs = []
            self.refresh_codex_status()
            return
        self._start_next_agent_run()

    def _show_claim_warning_if_needed(self, conversation_id: int, warning: str) -> None:
        if not warning:
            return
        self.database.add_message(conversation_id, "system", warning, status="warning")
        self.database.log_event("unsupported_claim_warning", warning[:500])
        self.chat.add_message("system", warning)

    def _record_work_result(
        self,
        worker: GenerateWorker | None,
        agent_key: str,
        content: str,
        parsed_response: ParsedAgentResponse,
        message_id: int,
        registered_artifacts: list[str],
    ) -> None:
        service = getattr(self, "work_context_service", None)
        if service is None:
            return
        context = service.get()
        if context is None:
            return
        artifact_ids = list(registered_artifacts)
        # A BOM first appears as a chat result in the common workflow. Keep it
        # addressable instead of forcing the next agent to guess from history.
        if (
            context.current_operation == IntentType.CREATE.value
            and "bom" in (self.pending_user_message or "").lower()
            and not any(
                row is not None and str(row["artifact_type"] or "").upper() == "BOM"
                for item in artifact_ids
                for row in [self.database.get_artifact(item)]
            )
        ):
            title = "DC_DC_5V_Buck BOM" if "ap63205" in content.lower() else "BOM из сообщения"
            try:
                artifact_ids.append(
                    self.artifact_service.register_chat_artifact(
                        content=content,
                        title=title,
                        artifact_type="BOM",
                        task_id=worker.task_id if worker is not None else context.task_id,
                        run_id=worker.run_id if worker is not None else None,
                        source_agent_id=agent_key,
                        source_message_id=message_id,
                    )
                )
            except Exception:
                self.logger.exception("chat_artifact_not_registered")
        rows = [row for item in artifact_ids if (row := self.database.get_artifact(item)) is not None]
        contract = getattr(self, "current_execution_contract", None)
        validation = self.output_validator.validate(contract, content, rows) if contract is not None else None
        if validation is not None and not validation.accepted:
            self.database.log_event("work_output_rejected", f"{agent_key}; {validation.code}")
            warning = f"Результат {agent_key} не принят: {validation.message}"
            self.database.add_message(self.conversation_id, "system", warning, status="warning")
            self.chat.add_message("system", warning)
        elif validation is not None:
            self.database.log_event("work_output_validated", f"{agent_key}; {validation.code}")
        service.record_result(
            artifact_ids=(artifact_ids if validation is None or validation.accepted else list(context.active_artifact_ids)),
            action=f"{agent_key}: {context.current_operation}",
            validation=validation or type("Validation", (), {"accepted": True, "code": "OK"})(),
        )
        self._refresh_work_context_strip()

    def _response_speaker_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for agent in self._chat_agents():
            aliases[agent.key] = agent.key
            aliases[agent.display_name] = agent.key
            for alias in agent.aliases:
                aliases[alias] = agent.key
        return aliases

    @staticmethod
    def _display_text_from_parsed_response(parsed_response: ParsedAgentResponse) -> str:
        if parsed_response.human_text.strip():
            return parsed_response.human_text
        envelope = parsed_response.envelope
        if isinstance(envelope, dict):
            for key in ("summary", "message", "result"):
                value = envelope.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @staticmethod
    def _display_text_from_raw_response(content: str) -> str:
        parsed = parse_agent_response(content)
        display = MainWindow._display_text_from_parsed_response(parsed)
        return display or content

    def _import_structured_artifacts(self, worker: GenerateWorker | None, parsed_response: ParsedAgentResponse, agent_key: str) -> list[str]:
        if not parsed_response.has_valid_envelope:
            return []
        try:
            registered = self.artifact_service.import_from_structured_response(
                envelope=parsed_response.envelope,
                task_id=worker.task_id if worker is not None else None,
                run_id=worker.run_id if worker is not None else None,
            )
        except Exception as exc:
            self.database.log_event("structured_artifacts_import_failed", f"{agent_key}: {exc}"[:500])
            return []
        if registered:
            self.database.log_event("structured_artifacts_imported", f"{agent_key}: {len(registered)}")
        return registered

    def _import_structured_findings(self, worker: GenerateWorker | None, parsed_response: ParsedAgentResponse, agent_key: str) -> list[str]:
        if not parsed_response.has_valid_envelope:
            return []
        try:
            created = self.finding_service.import_from_structured_response(
                envelope=parsed_response.envelope,
                task_id=worker.task_id if worker is not None else None,
                reviewer_run_id=worker.run_id if worker is not None else None,
                actor=agent_key,
            )
        except Exception as exc:
            self.database.log_event("structured_findings_import_failed", f"{agent_key}: {exc}"[:500])
            return []
        if created:
            self.database.log_event("structured_findings_imported", f"{agent_key}: {len(created)}")
            if worker is not None and worker.run_id:
                recorded = self.knowledge_application_service.record_standard_misapplications_from_findings(
                    finding_ids=created,
                    run_id=worker.run_id,
                    task_id=worker.task_id,
                    role=parsed_response.envelope.get("role", "") if isinstance(parsed_response.envelope, dict) else "",
                    actor=agent_key,
                )
                if recorded:
                    self.database.log_event("structured_finding_standard_misapplied", f"{agent_key}: {recorded}")
            if worker is not None and worker.task_id:
                try:
                    self.artifact_service.reconcile_finding_links(task_id=worker.task_id, actor=agent_key)
                except Exception as exc:
                    self.database.log_event("artifact_finding_reconcile_failed", f"{agent_key}: {exc}"[:500])
        return created

    def _import_structured_usage(self, worker: GenerateWorker | None, parsed_response: ParsedAgentResponse, agent_key: str):
        if not parsed_response.has_valid_envelope:
            return None
        try:
            result = self.knowledge_application_service.import_from_structured_response(
                envelope=parsed_response.envelope,
                task_id=worker.task_id if worker is not None else None,
                run_id=worker.run_id if worker is not None else None,
                actor=agent_key,
            )
        except Exception as exc:
            self.database.log_event("structured_usage_import_failed", f"{agent_key}: {exc}"[:500])
            return None
        if result.knowledge_recorded or result.standards_recorded:
            self.database.log_event(
                "structured_usage_imported",
                f"{agent_key}: knowledge={result.knowledge_recorded}; standards={result.standards_recorded}; rejected={result.rejected}",
            )
        return result

    def _record_learning_evidence(self, worker: GenerateWorker | None, summary: str) -> None:
        if worker is None or not worker.run_id:
            return
        try:
            record = self.learning_evidence_service.record_completed_run(
                worker.run_id,
                organization_id=self.active_organization_id,
                summary=summary,
            )
            if record is not None:
                self.database.log_event("experience_record_created", record.record_id)
        except Exception:
            self.logger.exception("experience_record_not_created")

    def stop_generation(self) -> None:
        self._clear_goal_state()
        self.exchange_turn = 0
        self.exchange_turn_limit = 0
        self.exchange_responded_agent_keys = set()
        self.exchange_fingerprints = []
        self.queued_user_message = None
        workers = list(self.active_workers.values())
        if self.worker is not None and self.worker not in workers:
            workers.append(self.worker)
        self.interrupting_current_run = bool(workers)
        self.cancellation_in_progress = bool(workers)
        self.chat.discard_stream()
        self._stop_response_latency_timers()
        if workers:
            self.pending_agent_keys = []
            self.pending_contextual_handoffs = []
            for worker in workers:
                worker.cancel()
            self.database.log_event("agent_cancel_requested", self.current_agent_key)
        else:
            self.cancellation_in_progress = False
            self.pending_agent_keys = []
            self.pending_user_message = ""
            self.last_peer_context = ""
            self.pending_contextual_handoffs = []
            self.chat.set_busy(False)

    def start_login(self) -> None:
        try:
            self.auth_service.start_login()
            QTimer.singleShot(3000, self.refresh_codex_status)
        except FileNotFoundError:
            self.refresh_codex_status()
            show_install_instructions(self)

    def _auth_action(self) -> None:
        if self.codex_authorized:
            self.logout()
        else:
            self.start_login()

    def show_director_console_preview(self) -> None:
        dialog = DirectorConsoleDialog(
            self.management_service,
            self.provider_registry,
            self.provider_health_service,
            self.provider_provisioning_service,
            self.skill_progress_service,
            self.skill_package_service,
            self.knowledge_service,
            self.standards_service,
            self.artifact_service,
            self.finding_service,
            self.product_metrics_service,
            self.universal_platform_service,
            str(self.settings.get("interface_language", "ru")),
            self.paths.avatar_dir,
            self,
        )
        dialog.exec()
        self.provider_provisioning_service.ensure_assignments_for_existing_agents()
        active_organization_id = self.database.get_active_organization_id()
        if active_organization_id != self.active_organization_id and active_organization_id:
            self._activate_organization_live(active_organization_id)
        elif active_organization_id is None and self.active_organization_id:
            self.active_organization_id = None
            self.conversation_id = self.database.ensure_general_conversation()
            self.universal_platform_service.conversation_id = self.conversation_id
            self.thread_service = ConversationThreadService(self.database, self.conversation_id)
            self.current_thread_id = self.thread_service.thread_id
            self.thread_question_service = ThreadQuestionService(self.database, self.conversation_id)
            self.work_context_service = WorkContextService(self.database, self.conversation_id, self.current_thread_id)
            self.conversation_mode = ConversationMode.SOCIAL
            self.load_conversation()
            self._refresh_work_context_strip()
        else:
            self._refresh_organization_selector()
            self._refresh_chat_agents()
        self._update_empty_team_state()

    def logout(self) -> None:
        status = self.auth_service.logout()
        QMessageBox.information(self, "Codex", status.message)
        self.refresh_codex_status()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != SettingsDialog.Accepted:
            return
        old_workspace = str(self.settings.get("workspace_root", ""))
        values = dialog.values()
        self.settings.update(values)
        self.settings_service.save(self.settings)
        self.chat_sound_service.configure(self.settings)
        self.team_router.general_chat_response = str(self.settings.get("general_chat_response", "SINGLE")).upper()
        self.codex_client.timeout_seconds = int(self.settings.get("codex_timeout_seconds", 180))
        self.gemini_client.timeout_seconds = int(self.settings.get("codex_timeout_seconds", 180))
        new_workspace = str(self.settings.get("workspace_root", ""))
        if new_workspace and new_workspace != old_workspace:
            self.workspace_service = WorkspaceService(Path(new_workspace))
            self.workspace_service.ensure()
            self.settings["workspace_root"] = str(self.workspace_service.root)
            self.settings_service.save(self.settings)
            self.codex_client.workspace = self.workspace_service.chat_runtime
            self.gemini_client.workspace = self.workspace_service.gemini_runtime
            self.skill_progress_service = SkillProgressService(self.database, self.skill_service, self.workspace_service.root)
            self.product_metrics_service = ProductMetricsService(self.database, self.skill_progress_service)
            self._update_workspace_status()
        self.apply_theme()
        self.chat.set_language(str(self.settings.get("interface_language", "ru")))
        self._refresh_chat_agents()
        self.refresh_codex_status()

    def choose_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Выбрать рабочую папку", str(self.workspace_service.root))
        if not selected:
            return
        self.workspace_service = WorkspaceService(Path(selected))
        self.workspace_service.ensure()
        self.settings["workspace_root"] = str(self.workspace_service.root)
        self.settings_service.save(self.settings)
        self.codex_client.workspace = self.workspace_service.chat_runtime
        self.gemini_client.workspace = self.workspace_service.gemini_runtime
        self.skill_progress_service = SkillProgressService(self.database, self.skill_service, self.workspace_service.root)
        self.product_metrics_service = ProductMetricsService(self.database, self.skill_progress_service)
        self._update_workspace_status()

    def open_workspace(self) -> None:
        try:
            import os
            os.startfile(str(self.workspace_service.root))
        except OSError as exc:
            QMessageBox.warning(self, "Рабочая папка", str(exc))

    def _update_workspace_status(self) -> None:
        info = self.workspace_service.info()
        if hasattr(self, "workspace_path_label"):
            self.workspace_path_label.setText(f"{info.root}\n● изолирована · доступна: {'да' if info.available else 'нет'}")
        self.workspace_status_label.setText(f"Рабочая папка: {info.root}")

    def _toggle_navigation(self) -> None:
        collapsed = self.nav_panel.width() <= 100
        if collapsed:
            self.nav_panel.setMinimumWidth(220)
            self.nav_panel.setMaximumWidth(320)
            self.main_splitter.setSizes([270, max(420, self.chat_panel.width()), self.inspector_panel.width()])
        else:
            self.nav_panel.setMinimumWidth(56)
            self.nav_panel.setMaximumWidth(56)
            self.main_splitter.setSizes([56, max(420, self.chat_panel.width() + self.nav_panel.width() - 56), self.inspector_panel.width()])

    def show_about_team(self) -> None:
        QMessageBox.information(
            self,
            "О команде",
            "Сотрудники работают через назначенные AI-провайдеры.\n"
            "Обращайтесь к сотруднику по имени или выберите его в поле адресата.\n"
            "Если исполнитель не указан, маршрутизатор выберет подходящего сотрудника.\n\n"
            f"Сборка: {build_label()}",
        )

    def apply_theme(self) -> None:
        theme = str(self.settings.get("theme", "dark"))
        from PySide6.QtWidgets import QApplication

        qt_app = QApplication.instance()
        if qt_app is not None:
            qt_app.setPalette(ThemeManager.palette(theme))
            qt_app.setStyleSheet(ThemeManager.stylesheet(theme))
        self.setStyleSheet(ThemeManager.stylesheet(theme))
        self._apply_native_window_chrome(theme)
        if hasattr(self, "chat_panel") and isinstance(self.chat_panel, ThemeBackdrop):
            self.chat_panel.set_theme(theme)
            self.chat_panel.set_background(
                str(self.settings.get("chat_background_path", "")),
                int(self.settings.get("chat_background_opacity", 18)),
                str(self.settings.get("chat_background_mode", "cover")),
            )
        if bool(self.settings.get("reduce_motion", False)) or not self.isVisible():
            return
        self._theme_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._theme_animation.setDuration(180)
        self._theme_animation.setStartValue(0.92)
        self._theme_animation.setEndValue(1.0)
        self._theme_animation.start()

    def _apply_native_window_chrome(self, theme: str) -> None:
        """Tint the native Windows frame while retaining snap/resize behavior."""
        try:
            import ctypes
            import os

            if os.name != "nt":
                return
            colors = ThemeManager.native_chrome_colors(theme)
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            use_dark = ctypes.c_int(1 if colors[0] else 0)
            caption = ctypes.c_uint(colors[1])
            text = ctypes.c_uint(colors[2])
            border = ctypes.c_uint(colors[3])
            for attribute, value in ((20, use_dark), (35, caption), (36, text), (34, border)):
                dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        except (AttributeError, OSError, TypeError, ValueError):
            # Older Windows builds or non-Windows test runners simply keep the
            # native frame defaults.
            self.logger.debug("native_window_chrome_unavailable", exc_info=True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    def _restore_window_state(self) -> None:
        state = QSettings("Roman2050", "Roman2050")
        geometry = state.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event) -> None:
        state = QSettings("Roman2050", "Roman2050")
        state.setValue("geometry", self.saveGeometry())
        if self.worker is not None:
            self._stop_response_latency_timers()
            self.worker.cancel()
            self.worker.wait(5000)
        super().closeEvent(event)
