from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from autoee_demo.model_backend import ChatGPTOAuthPlaceholder, KeyringSecretStore, ModelManager, ProviderConfig


WORKFLOW_STEPS = [
    "spec_analyzer",
    "component_search",
    "loss_thermal",
    "kicad_freecad",
    "report_generator",
]


class ModelBackendDialog(QtWidgets.QDialog):
    def __init__(self, manager: ModelManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Model Backend Settings")
        self.resize(720, 520)

        self.provider_combo = QtWidgets.QComboBox()
        self.provider_combo.addItems(self.manager.registry.names())
        self.provider_combo.setCurrentText(self.manager.settings.default_provider)

        self.model_edit = QtWidgets.QLineEdit()
        self.base_url_edit = QtWidgets.QLineEdit()
        self.env_edit = QtWidgets.QLineEdit()
        self.secret_name_edit = QtWidgets.QLineEdit()
        self.api_key_edit = QtWidgets.QLineEdit()
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Optional: save/update key in OS keyring")

        self.default_checkbox = QtWidgets.QCheckBox("Use as default provider")
        self.default_checkbox.setChecked(True)

        self.oauth_label = QtWidgets.QLabel(ChatGPTOAuthPlaceholder().describe())
        self.oauth_label.setWordWrap(True)

        self.step_table = QtWidgets.QTableWidget(len(WORKFLOW_STEPS), 2)
        self.step_table.setHorizontalHeaderLabels(["Workflow step", "Provider override"])
        self.step_table.horizontalHeader().setStretchLastSection(True)
        for row, step in enumerate(WORKFLOW_STEPS):
            self.step_table.setItem(row, 0, QtWidgets.QTableWidgetItem(step))
            combo = QtWidgets.QComboBox()
            combo.addItem("(global default)")
            combo.addItems(self.manager.registry.names())
            combo.setCurrentText(self.manager.settings.per_step_overrides.get(step, "(global default)"))
            self.step_table.setCellWidget(row, 1, combo)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.addRow("Provider", self.provider_combo)
        form.addRow("Model ID", self.model_edit)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("API key env var", self.env_edit)
        form.addRow("Keyring secret name", self.secret_name_edit)
        form.addRow("API key", self.api_key_edit)
        form.addRow("", self.default_checkbox)

        self.test_button = QtWidgets.QPushButton("Test connection")
        self.save_button = QtWidgets.QPushButton("Save")
        self.cancel_button = QtWidgets.QPushButton("Cancel")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.test_button)
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QtWidgets.QLabel("Per-step provider override"))
        layout.addWidget(self.step_table)
        layout.addWidget(QtWidgets.QLabel("ChatGPT OAuth"))
        layout.addWidget(self.oauth_label)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

        self.provider_combo.currentTextChanged.connect(self.load_provider_config)
        self.test_button.clicked.connect(self.test_connection)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)
        self.load_provider_config(self.provider_combo.currentText())

    def load_provider_config(self, provider_name: str) -> None:
        config = self.manager.settings.configs.get(provider_name) or self.manager.registry.default_config(provider_name)
        self.model_edit.setText(config.model)
        self.base_url_edit.setText(config.base_url)
        self.env_edit.setText(config.api_key_env)
        self.secret_name_edit.setText(config.secret_name)
        self.api_key_edit.clear()
        self.default_checkbox.setChecked(provider_name == self.manager.settings.default_provider)

    def current_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider=self.provider_combo.currentText(),
            model=self.model_edit.text().strip(),
            base_url=self.base_url_edit.text().strip(),
            api_key_env=self.env_edit.text().strip(),
            secret_name=self.secret_name_edit.text().strip(),
        )

    def save(self) -> None:
        config = self.current_config()
        self.manager.settings.set_provider_config(config)
        if self.default_checkbox.isChecked():
            self.manager.settings.default_provider = config.provider
        api_key = self.api_key_edit.text().strip()
        if api_key:
            if isinstance(self.manager.secret_store, KeyringSecretStore) or KeyringSecretStore.available():
                self.manager.secret_store.set_secret(config.secret_name, api_key)
            else:
                self.status.setText("Warning: keyring is unavailable; API key was not persisted.")
        for row, step in enumerate(WORKFLOW_STEPS):
            combo = self.step_table.cellWidget(row, 1)
            if combo is None:
                continue
            value = combo.currentText()
            if value == "(global default)":
                self.manager.settings.per_step_overrides.pop(step, None)
            else:
                self.manager.settings.per_step_overrides[step] = value
        saved_path = self.manager.save_settings()
        self.status.setText(f"Saved model backend settings to {saved_path}")
        QtCore.QTimer.singleShot(400, self.accept)

    def test_connection(self) -> None:
        self.manager.settings.set_provider_config(self.current_config())
        health = self.manager.health_check(self.provider_combo.currentText())
        self.status.setText(f"{health.provider}: {health.message} [{health.fingerprint}]")

