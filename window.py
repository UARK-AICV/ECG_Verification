from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QAbstractSpinBox
)

from action import (
    create_box,
    distribute_runs_uniformly,
    persist_sample,
    remove_all_for_label_in_lead,
    remove_entry_run,
    update_entry_run,
)
from constants import PROCESSED_ROOT
from data_utils import add_label_definition, discover_sample_files, get_label_definitions, group_entries_by_lead, label_color, lead_sort_key, load_sample_bundle, normalize_lead_name
from views import LeadDetailView, LeadOverviewView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ECG Labelling Tool")
        self.resize(1720, 1080)

        self.sample_files = discover_sample_files(PROCESSED_ROOT)
        self.current_index = 0
        self.current_sample = None
        self.current_signal = None
        self.current_leads = []
        self.current_mode = "overview"
        self.current_lead = None
        self.current_sample_file = None
        self.first_anchor = None
        self.last_anchor = None
        self.visible_labels = set()
        self.measure_mode = False

        self.setStyleSheet(
            """
            QMainWindow { background-color: #f3efe6; }
            QLabel#title { font-size: 22px; font-weight: 700; color: #1d2a38; }
            QLabel#meta { color: #54606d; font-size: 13px; }
            QLabel#sampleCounter { color: #1d2a38; font-size: 18px; font-weight: 700; }
            QLabel#warning {
                background-color: #f6d9a2;
                color: #6f4d1f;
                padding: 8px 10px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton {
                background-color: #2d6a4f;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #24563f; }
            QPushButton:disabled { background-color: #b8c7bd; }
            QFrame#sidePanel {
                background-color: #e8dcc7;
                border: 1px solid #d9d1c3;
                border-radius: 8px;
            }
            QScrollArea#labelScrollArea, QWidget#labelScrollWidget {
                background-color: white;
            }
            QComboBox {
                background-color: white;
                padding: 6px 8px;
                border: 1px solid #d9d1c3;
                border-radius: 6px;
            }
            QLabel#displaySectionTitle, QLabel#createSectionTitle {
                color: #24563f;
                font-weight: 700;
            }
            """
        )

        self.overview_view = LeadOverviewView(self.open_lead_detail)
        self.detail_view = LeadDetailView(
            self.on_span_selected,
            self.on_span_changed,
            self.create_box_for_current_lead,
            self.update_measurement_label,
        )

        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warning")
        self.warning_label.hide()

        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.sample_counter = QLabel("Sample 0/0")
        self.sample_counter.setObjectName("sampleCounter")
        self.sample_counter.setAlignment(Qt.AlignCenter)
        self.full_view_button = QPushButton("Home")
        self.delete_span_button = QPushButton("Delete")
        self.delete_lead_button = QPushButton("Delete All")
        self.mark_first_button = QPushButton("Mark First")
        self.mark_last_button = QPushButton("Mark Last")
        self.distribute_button = QPushButton("Uniform Fill")
        self.measure_button = QPushButton("Measure")
        self.measure_button.setCheckable(True)
        self.measurement_label = QLabel("")
        self.measurement_label.setObjectName("meta")
        self.box_count_input = QSpinBox()
        self.box_count_input.setMinimum(1)
        self.box_count_input.setMaximum(50)
        self.box_count_input.setValue(3)
        self.box_count_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        self.box_count_input.setStyleSheet(
            """
            QSpinBox {
                background-color: #dcebdc;
                color: #1f4d3a;
                border: 1px solid #9fbaa8;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QSpinBox:hover {
                border: 1px solid #7fa08b;
            }
            QSpinBox:focus {
                border: 1px solid #5f8f74;
            }
            """
        )
        self.lead_combo = QComboBox()
        self.lead_combo.setObjectName("leadCombo")
        self.lead_combo.setMinimumWidth(80)
        self.disease_combo = QComboBox()
        self.disease_combo.setObjectName("diseaseCombo")
        self.disease_combo.setMinimumWidth(220)
        self.create_button = QPushButton("Create")
        self.add_custom_label_button = QPushButton("Add Custom Label")

        self.refresh_disease_combo()
        self.update_disease_combo_style()
        self.update_lead_combo_style()

        self.prev_button.clicked.connect(self.prev_sample)
        self.next_button.clicked.connect(self.next_sample)
        self.full_view_button.clicked.connect(self.show_full_leads)
        self.delete_span_button.clicked.connect(self.delete_selected_span)
        self.delete_lead_button.clicked.connect(self.delete_all_in_current_lead)
        self.mark_first_button.clicked.connect(self.mark_first_span)
        self.mark_last_button.clicked.connect(self.mark_last_span)
        self.distribute_button.clicked.connect(self.uniform_fill_between_anchors)
        self.measure_button.toggled.connect(self.toggle_measure_mode)
        self.create_button.clicked.connect(self.start_create_box)
        self.add_custom_label_button.clicked.connect(self.add_custom_label)
        self.lead_combo.currentTextChanged.connect(self.on_lead_changed)
        self.disease_combo.currentTextChanged.connect(self.update_disease_combo_style)

        self.delete_span_button.setDisabled(True)
        self.delete_lead_button.setDisabled(True)
        self.mark_first_button.setDisabled(True)
        self.mark_last_button.setDisabled(True)
        self.distribute_button.setDisabled(True)

        self.legend_layout = QVBoxLayout()
        self.legend_layout.setAlignment(Qt.AlignTop)

        legend_container = QWidget()
        legend_container.setObjectName("labelScrollWidget")
        legend_container.setLayout(self.legend_layout)

        legend_scroll = QScrollArea()
        legend_scroll.setObjectName("labelScrollArea")
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setWidget(legend_container)
        legend_scroll.setFrameShape(QFrame.NoFrame)

        side_panel = QFrame()
        side_panel.setObjectName("sidePanel")
        side_layout = QVBoxLayout(side_panel)
        display_title = QLabel("Display Labels")
        display_title.setObjectName("displaySectionTitle")
        side_layout.addWidget(display_title)
        side_layout.addWidget(legend_scroll, 1)
        side_layout.addSpacing(10)
        create_title = QLabel("Create Label")
        create_title.setObjectName("createSectionTitle")
        side_layout.addWidget(create_title)
        side_layout.addWidget(self.disease_combo)
        side_layout.addWidget(self.create_button)
        side_layout.addWidget(self.add_custom_label_button)
        side_panel.setMinimumWidth(220)
        side_panel.setMaximumWidth(280)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.delete_span_button)
        top_bar.addWidget(self.delete_lead_button)
        top_bar.addWidget(self.mark_first_button)
        top_bar.addWidget(self.mark_last_button)
        top_bar.addWidget(self.box_count_input)
        top_bar.addWidget(self.distribute_button)
        top_bar.addWidget(self.measure_button)
        top_bar.addWidget(self.measurement_label)
        top_bar.addWidget(self.lead_combo)
        navigation_bar = QHBoxLayout()
        navigation_bar.addStretch()
        navigation_bar.addWidget(self.prev_button)
        navigation_bar.addWidget(self.next_button)
        navigation_bar.addWidget(self.full_view_button)

        left_controls = QWidget()
        left_controls.setLayout(top_bar)
        right_controls = QWidget()
        right_controls.setLayout(navigation_bar)
        for controls in (left_controls, right_controls):
            controls.layout().setContentsMargins(0, 0, 0, 0)
            controls.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        header = QGridLayout()
        header.setColumnStretch(0, 1)
        header.setColumnStretch(2, 1)
        header.addWidget(left_controls, 0, 0)
        header.addWidget(self.sample_counter, 0, 1)
        header.addWidget(right_controls, 0, 2)

        center = QHBoxLayout()
        center.addWidget(self.overview_view, 1)
        center.addWidget(self.detail_view, 1)
        center.addWidget(side_panel)

        root_layout = QVBoxLayout()
        root_layout.addLayout(header)
        root_layout.addWidget(self.warning_label)
        root_layout.addLayout(center, 1)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

        self.detail_view.hide()
        self.full_view_button.hide()
        self.delete_span_button.hide()
        self.delete_lead_button.hide()
        self.mark_first_button.hide()
        self.mark_last_button.hide()
        self.box_count_input.hide()
        self.distribute_button.hide()
        self.measure_button.hide()
        self.measurement_label.hide()
        self.lead_combo.hide()
        self.disease_combo.hide()
        self.create_button.hide()
        self.add_custom_label_button.hide()
        self.load_current_sample()

    def clear_anchors(self):
        self.first_anchor = None
        self.last_anchor = None
        self.update_anchor_label()
        self.update_distribute_button()

    def update_anchor_label(self):
        pass

    def update_disease_combo_style(self):
        self.disease_combo.setStyleSheet(
            """
            QComboBox#diseaseCombo {
                background-color: #dcebdc;
                color: #1f4d3a;
                padding: 6px 8px;
                border: 1px solid #9fbaa8;
                border-radius: 6px;
            }
            QComboBox#diseaseCombo:hover {
                border: 1px solid #7fa08b;
            }
            QComboBox#diseaseCombo:focus {
                border: 1px solid #5f8f74;
            }
            QComboBox#diseaseCombo QAbstractItemView {
                background-color: white;
                color: #1d2a38;
                selection-background-color: #dcebdc;
                selection-color: #1f4d3a;
                font: 16px;
            }
            """
        )


    def update_lead_combo_style(self):
        self.lead_combo.setFixedWidth(80)

        self.lead_combo.setStyleSheet(
            """
            QComboBox#leadCombo {
                background-color: #eef2f0;
                color: #1f4d3a;
                padding: 8px 14px;
                border: 1px solid #b8c4bd;
                border-radius: 6px;
            }
            QComboBox#leadCombo:hover {
                border: 1px solid #98aaa0;
            }
            QComboBox#leadCombo:focus {
                border: 1px solid #7f9689;
            }
            QComboBox#leadCombo QAbstractItemView {
                background-color: #eef2f0;
                color: #1d2a38;
                selection-background-color: #dbe8df;
                selection-color: #1d2a38;
            }
            """
        )

    def refresh_disease_combo(self, selected_label=None):
        labels = [item["name"] for item in get_label_definitions()]
        current_label = selected_label if selected_label is not None else self.disease_combo.currentText()
        self.disease_combo.blockSignals(True)
        self.disease_combo.clear()
        self.disease_combo.addItems(labels)
        if current_label and current_label in labels:
            self.disease_combo.setCurrentText(current_label)
        self.disease_combo.blockSignals(False)

    def add_custom_label(self):
        label_name, accepted = QInputDialog.getText(self, "Add Custom Label", "Label name:")
        if not accepted:
            return

        label_name = label_name.strip()
        if not label_name:
            QMessageBox.warning(self, "Invalid Label", "Label name cannot be empty.")
            return

        color = QColorDialog.getColor(QColor("#1f77b4"), self, "Choose Label Color")
        if not color.isValid():
            return

        try:
            add_label_definition(label_name, color.name())
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Add Label", str(exc))
            return

        self.refresh_disease_combo(selected_label=label_name)
        self.update_disease_combo_style()
        self.update_legend()

    def actual_labels(self):
        if self.current_sample is None:
            return set()
        entries = self.current_sample.get("entries", [])
        if self.current_mode == "detail" and self.current_lead is not None:
            entries = [
                entry
                for entry in entries
                if normalize_lead_name(entry.get("lead", "")) == self.current_lead
            ]
        return {entry.get("label", "unknown") for entry in entries}

    def update_distribute_button(self):
        ready = (
            self.first_anchor is not None
            and self.last_anchor is not None
            and self.current_mode == "detail"
            and self.first_anchor["entry"] is self.last_anchor["entry"]
            and self.first_anchor["run_index"] != self.last_anchor["run_index"]
        )
        self.distribute_button.setEnabled(ready)

    def clear_legend(self):
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def update_legend(self):
        self.clear_legend()

        if not self.current_sample:
            self.legend_layout.addWidget(QLabel("No sample loaded."))
            return

        entries = self.current_sample.get("entries", [])
        if self.current_mode == "detail" and self.current_lead is not None:
            entries = [
                entry
                for entry in entries
                if normalize_lead_name(entry.get("lead", "")) == self.current_lead
            ]
        if not entries:
            return

        labels = sorted(self.actual_labels())
        labels = ["All"] + labels
        actual_labels = self.actual_labels()

        for label_name in labels:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            checkbox = QCheckBox()
            if label_name == "All":
                checkbox.setChecked(self.visible_labels == actual_labels)
            else:
                checkbox.setChecked(label_name in self.visible_labels)
            checkbox.toggled.connect(lambda checked, name=label_name: self.toggle_label_visibility(name, checked))

            label_widget = QLabel(label_name)
            label_widget.setWordWrap(True)
            if label_name == "All":
                label_widget.setStyleSheet("color: #203040; font-weight: 700;")
            else:
                label_widget.setStyleSheet(f"color: {label_color(label_name).name()}; font-weight: 700;")

            row_layout.addWidget(checkbox, 0)
            row_layout.addWidget(label_widget, 1)
            self.legend_layout.addWidget(row)

        self.legend_layout.addStretch()

    def toggle_label_visibility(self, label_name, is_checked):
        actual_labels = self.actual_labels()
        if label_name == "All":
            if is_checked:
                self.visible_labels |= set(actual_labels)
            else:
                self.visible_labels -= set(actual_labels)
        else:
            if is_checked:
                self.visible_labels.add(label_name)
            else:
                self.visible_labels.discard(label_name)
        self.redraw_current_view()
        self.update_legend()

    def redraw_current_view(self):
        if self.current_sample is None or self.current_signal is None:
            return
        if self.current_mode == "overview":
            self.overview_view.draw_sample(
                self.current_sample,
                self.current_signal,
                self.current_leads,
                self.visible_labels,
            )
        elif self.current_mode == "detail" and self.current_lead is not None:
            self.open_lead_detail(self.current_lead)

    def update_measurement_label(self, text):
        self.measurement_label.setText(text)

    def toggle_measure_mode(self, enabled):
        self.measure_mode = enabled
        self.detail_view.set_measure_mode(enabled)
        if enabled:
            self.detail_view.set_create_mode(False)
        if not enabled:
            self.update_measurement_label("")
    def load_current_sample(self):
        sample_number = self.current_index + 1 if self.sample_files else 0
        self.sample_counter.setText(f"Sample {sample_number}/{len(self.sample_files)}")
        if not self.sample_files:
            self.current_sample = None
            self.setWindowTitle("ECG Labelling Tool")
            self.warning_label.setText("The fixed processed dataset path does not contain any label.json files.")
            self.warning_label.show()
            self.prev_button.setDisabled(True)
            self.next_button.setDisabled(True)
            self.overview_view.draw_sample({}, None, [])
            self.update_legend()
            return

        sample_file = self.sample_files[self.current_index]
        self.current_sample_file = sample_file
        self.current_sample, self.current_signal, self.current_leads = load_sample_bundle(sample_file)

        sample_id = self.current_sample.get("sample_id", sample_file.parent.name)
        entries = self.current_sample.get("entries", [])
        self.setWindowTitle(f"ECG Labelling Tool |  {self.current_index + 1}/{len(self.sample_files)}")
        self.visible_labels = {entry.get("label", "unknown") for entry in entries}

        self.warning_label.hide()

        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.sample_files) - 1)
        self.lead_combo.blockSignals(True)
        self.lead_combo.clear()
        for raw_lead in self.current_leads:
            self.lead_combo.addItem(normalize_lead_name(raw_lead))
        self.lead_combo.blockSignals(False)
        self.update_lead_combo_style()

        self.current_mode = "overview"
        self.current_lead = None
        self.clear_anchors()
        self.detail_view.set_create_mode(False)
        self.measure_button.blockSignals(True)
        self.measure_button.setChecked(False)
        self.measure_button.blockSignals(False)
        self.measure_mode = False
        self.detail_view.set_measure_mode(False)
        self.update_measurement_label("")
        self.overview_view.draw_sample(self.current_sample, self.current_signal, self.current_leads, self.visible_labels)
        self.overview_view.show()
        self.detail_view.hide()
        self.full_view_button.hide()
        self.delete_span_button.hide()
        self.delete_lead_button.hide()
        self.mark_first_button.hide()
        self.mark_last_button.hide()
        self.box_count_input.hide()
        self.distribute_button.hide()
        self.measure_button.hide()
        self.measurement_label.hide()
        self.lead_combo.hide()
        self.disease_combo.hide()
        self.create_button.hide()
        self.add_custom_label_button.hide()
        self.delete_span_button.setDisabled(True)
        self.delete_lead_button.setDisabled(True)
        self.mark_first_button.setDisabled(True)
        self.mark_last_button.setDisabled(True)
        self.update_legend()

    def open_lead_detail(self, lead_name):
        if self.current_sample is None or self.current_signal is None:
            return

        lead_lookup = {
            normalize_lead_name(raw_lead): index
            for index, raw_lead in enumerate(self.current_leads)
        }
        signal_index = lead_lookup.get(lead_name)
        if signal_index is None:
            return

        entries = group_entries_by_lead(self.current_sample.get("entries", [])).get(lead_name, [])
        sample_id = self.current_sample.get("sample_id", "unknown")
        self.detail_view.draw_lead(sample_id, lead_name, self.current_signal[:, signal_index], entries, self.visible_labels)
        self.current_mode = "detail"
        self.current_lead = lead_name
        self.detail_view.set_create_mode(False)
        self.detail_view.set_measure_mode(self.measure_mode)
        self.overview_view.hide()
        self.detail_view.show()
        self.full_view_button.show()
        self.delete_span_button.show()
        self.delete_lead_button.show()
        self.mark_first_button.show()
        self.mark_last_button.show()
        self.box_count_input.show()
        self.distribute_button.show()
        self.measure_button.show()
        self.measurement_label.show()
        self.lead_combo.show()
        self.disease_combo.show()
        self.create_button.show()
        self.add_custom_label_button.show()
        self.lead_combo.blockSignals(True)
        self.lead_combo.setCurrentText(lead_name)
        self.lead_combo.blockSignals(False)
        self.delete_span_button.setDisabled(True)
        self.delete_lead_button.setEnabled(True)
        self.mark_first_button.setDisabled(True)
        self.mark_last_button.setDisabled(True)
        self.update_distribute_button()
        self.update_legend()

    def show_full_leads(self):
        if self.current_sample is None or self.current_signal is None:
            return

        self.current_mode = "overview"
        self.current_lead = None
        self.clear_anchors()
        self.detail_view.set_create_mode(False)
        self.detail_view.set_measure_mode(False)
        self.measure_button.blockSignals(True)
        self.measure_button.setChecked(False)
        self.measure_button.blockSignals(False)
        self.measure_mode = False
        self.update_measurement_label("")
        self.overview_view.draw_sample(self.current_sample, self.current_signal, self.current_leads, self.visible_labels)
        self.detail_view.hide()
        self.overview_view.show()
        self.full_view_button.hide()
        self.delete_span_button.hide()
        self.delete_lead_button.hide()
        self.mark_first_button.hide()
        self.mark_last_button.hide()
        self.box_count_input.hide()
        self.distribute_button.hide()
        self.measure_button.hide()
        self.measurement_label.hide()
        self.lead_combo.hide()
        self.disease_combo.hide()
        self.create_button.hide()
        self.add_custom_label_button.hide()
        self.delete_span_button.setDisabled(True)
        self.delete_lead_button.setDisabled(True)
        self.mark_first_button.setDisabled(True)
        self.mark_last_button.setDisabled(True)
        self.update_legend()

    def on_span_selected(self, span_item):
        is_detail = self.current_mode == "detail"
        has_selection = span_item is not None and is_detail
        self.delete_span_button.setEnabled(has_selection)
        self.mark_first_button.setEnabled(has_selection)
        self.mark_last_button.setEnabled(has_selection)
        if span_item is not None:
            self.disease_combo.blockSignals(True)
            self.disease_combo.setCurrentText(span_item["label"])
            self.disease_combo.blockSignals(False)
            self.update_disease_combo_style()
        self.update_distribute_button()

    def persist_labels(self):
        if self.current_sample is None or self.current_sample_file is None:
            return
        persist_sample(self.current_sample_file, self.current_sample)
        self.update_legend()

    def on_span_changed(self, span_item):
        if span_item is None:
            return
        update_entry_run(span_item["entry"], span_item["run_index"], span_item["start"], span_item["end"])
        self.persist_labels()
        self.clear_anchors()
        if self.current_lead is not None:
            self.open_lead_detail(self.current_lead)

    def delete_selected_span(self):
        span_item = self.detail_view.selected_span
        if span_item is None:
            return
        remove_entry_run(span_item["entry"], span_item["run_index"])
        self.persist_labels()
        self.clear_anchors()
        if self.current_lead is not None:
            self.open_lead_detail(self.current_lead)

    def delete_all_in_current_lead(self):
        if self.current_sample is None or self.current_lead is None:
            return
        span_item = self.detail_view.selected_span
        if span_item is None:
            return
        remove_all_for_label_in_lead(self.current_sample, self.current_lead, span_item["label"])
        self.persist_labels()
        self.clear_anchors()
        self.open_lead_detail(self.current_lead)

    def mark_first_span(self):
        span_item = self.detail_view.selected_span
        if span_item is None:
            return
        self.first_anchor = span_item
        self.update_anchor_label()
        self.update_distribute_button()

    def mark_last_span(self):
        span_item = self.detail_view.selected_span
        if span_item is None:
            return
        self.last_anchor = span_item
        self.update_anchor_label()
        self.update_distribute_button()

    def start_create_box(self):
        if self.current_mode != "detail" or self.current_lead is None:
            return
        self.measure_button.blockSignals(True)
        self.measure_button.setChecked(False)
        self.measure_button.blockSignals(False)
        self.measure_mode = False
        self.update_measurement_label("")
        self.detail_view.set_create_mode(True, self.disease_combo.currentText())

    def on_lead_changed(self, lead_name):
        if self.current_mode == "detail" and lead_name:
            self.open_lead_detail(lead_name)

    def create_box_for_current_lead(self, disease_name, start, end):
        if self.current_sample is None or self.current_lead is None or not disease_name:
            return
        create_box(self.current_sample, self.current_lead, disease_name, start, end)
        self.visible_labels.add(disease_name)
        self.persist_labels()
        self.clear_anchors()
        self.open_lead_detail(self.current_lead)

    def uniform_fill_between_anchors(self):
        if self.first_anchor is None or self.last_anchor is None:
            return
        if self.first_anchor["entry"] is not self.last_anchor["entry"]:
            return
        distribute_runs_uniformly(
            self.first_anchor["entry"],
            self.first_anchor["run_index"],
            self.last_anchor["run_index"],
            self.box_count_input.value(),
        )
        self.persist_labels()
        self.clear_anchors()
        if self.current_lead is not None:
            self.open_lead_detail(self.current_lead)

    def prev_sample(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_sample()

    def next_sample(self):
        if self.current_index < len(self.sample_files) - 1:
            self.current_index += 1
            self.load_current_sample()
