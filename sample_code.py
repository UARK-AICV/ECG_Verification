import sys
import os
import json
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QFrame, QComboBox, QScrollArea, QCheckBox
)
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF


# extracting the frame
def extract_frame_number(filename):
    match = re.search(r"\d+", filename)
    return int(match.group()) if match else None


# ---------- IMAGE VIEW ----------
class ImageView(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        
        self.setFocusPolicy(Qt.StrongFocus)

        self.zoom_factor = 1.15
        self.image_item = None

        self.is_drawing_mode = False  
        self.is_distribution_mode = False 
        self.is_currently_dragging = False 
        self.is_resizing_existing = False
        self.resize_item = None
        self.start_pos = None
        self.temp_rect = None
        self.current_label = None
        self.current_color = QColor("red")

    def load_image(self, path):
        self.scene.clear()
        pixmap = QPixmap(path)
        self.image_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(pixmap.rect())
        self.resetTransform()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def enable_drawing(self, label, color):
        self.is_drawing_mode = True
        self.current_label = label
        self.current_color = color
        self.cleanup_temp_rect()
        self.setFocus() 

    def disable_drawing(self):
        self.is_drawing_mode = False
        self.is_currently_dragging = False
        self.cleanup_temp_rect()
        self.unsetCursor()

    def cleanup_temp_rect(self):
        if self.temp_rect:
            self.scene.removeItem(self.temp_rect)
            self.temp_rect = None

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        
        if self.is_distribution_mode and event.button() == Qt.LeftButton:
            self.cleanup_temp_rect()
            self.start_pos = scene_pos
            self.temp_rect = QGraphicsRectItem()
            pen = QPen(QColor("yellow"), 2, Qt.DashDotLine)
            self.temp_rect.setPen(pen)
            self.temp_rect.setZValue(1000) 
            self.scene.addItem(self.temp_rect)
            event.accept()

        elif self.is_drawing_mode and event.button() == Qt.LeftButton:
            self.cleanup_temp_rect()
            self.is_currently_dragging = True
            self.start_pos = scene_pos
            self.temp_rect = QGraphicsRectItem()
            self.temp_rect.setPen(QPen(self.current_color, 3))
            fill_color = QColor(self.current_color)
            fill_color.setAlpha(50)
            self.temp_rect.setBrush(fill_color)
            self.temp_rect.setZValue(1000)
            self.scene.addItem(self.temp_rect)
            event.accept()
        else:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, QGraphicsRectItem) and item != self.image_item:
                rect = item.rect()
                if (abs(scene_pos.x() - (item.pos().x() + rect.right())) < 15 and 
                    abs(scene_pos.y() - (item.pos().y() + rect.bottom())) < 15):
                    self.is_resizing_existing = True
                    self.resize_item = item
                    self.start_pos = scene_pos
                    if isinstance(self.window(), MainWindow):
                        self.window().save_button.setEnabled(True)
                    event.accept()
                    return
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        
        if (self.is_currently_dragging or self.is_distribution_mode) and self.temp_rect:
            rect = QRectF(self.start_pos, scene_pos).normalized()
            self.temp_rect.setRect(rect)
            event.accept()
        elif self.is_resizing_existing and self.resize_item:
            new_width = max(5, scene_pos.x() - self.resize_item.pos().x())
            new_height = max(5, scene_pos.y() - self.resize_item.pos().y())
            self.resize_item.setRect(0, 0, new_width, new_height)
            event.accept()
        else:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, QGraphicsRectItem) and item != self.image_item:
                rect = item.rect()
                if (abs(scene_pos.x() - (item.pos().x() + rect.right())) < 15 and 
                    abs(scene_pos.y() - (item.pos().y() + rect.bottom())) < 15):
                    self.setCursor(Qt.SizeFDiagCursor)
                else:
                    self.unsetCursor()
            else:
                self.unsetCursor()
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_distribution_mode and self.temp_rect:
            path = QPainterPath()
            path.addRect(self.temp_rect.rect())
            self.scene.setSelectionArea(path)
            self.cleanup_temp_rect()
        
        self.is_currently_dragging = False
        self.is_resizing_existing = False
        self.resize_item = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.is_distribution_mode:
                self.window().exit_distribution_mode()
                event.accept()
                return
            if self.is_drawing_mode or self.temp_rect:
                self.disable_drawing()
                if isinstance(self.window(), MainWindow):
                    self.window().save_button.setDisabled(True)
                event.accept()
                return

        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            selected_items = self.scene.selectedItems()
            if selected_items:
                item = selected_items[0]
                if hasattr(item, 'annotation_ref'):
                    self.window().clipboard_data = item.annotation_ref.copy()
            event.accept()
            return

        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            if hasattr(self.window(), 'clipboard_data') and self.window().clipboard_data:
                self.window().paste_annotation()
            event.accept()
            return

        super().keyPressEvent(event)


# ---------- MAIN WINDOW ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Annotation Tool")
        self.resize(1200, 800)

        self.image_folder = None
        self.image_files = []
        self.current_index = 0
        self.current_frame = None
        self.annotations = []
        self.label_colors = {}
        self.visible_labels = set()
        self.clipboard_data = None

        self.setStyleSheet("""
            QMainWindow { background-color: #f5faff; }
            QPushButton {
                background-color: #4da3ff;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2f8cff; }
            QPushButton:disabled { background-color: #9ecbff; }
            QPushButton#distBtn { background-color: #6c757d; }
            QPushButton#distBtn:checked { background-color: #dc3545; }
            QPushButton.delete-label-btn {
                background-color: #ff4d4d;
                padding: 2px 6px;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton.delete-label-btn:hover { background-color: #cc0000; }
            QLabel#warning {
                background-color: #fff3cd;
                color: #856404;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

        self.image_view = ImageView()
        self.image_view.scene.selectionChanged.connect(self.on_selection_changed)

        self.select_button = QPushButton("Select Image Folder")
        self.save_button = QPushButton("Save")
        self.close_button = QPushButton("X Close")
        self.create_button = QPushButton("+ Create")
        self.delete_button = QPushButton("Delete")
        
        self.distribute_mode_btn = QPushButton("↔ Distribute Mode")
        self.distribute_mode_btn.setObjectName("distBtn")
        self.distribute_mode_btn.setCheckable(True)
        
        self.spacing_input = QComboBox()
        self.spacing_input.setEditable(True)
        self.spacing_input.setPlaceholderText("Spacing (px)")
        self.spacing_input.addItems(["0", "5", "10", "20", "50"])
        self.spacing_input.setFixedWidth(120)
        self.spacing_input.hide()
        
        self.apply_dist_btn = QPushButton("Apply Spacing")
        self.apply_dist_btn.hide()

        self.save_button.setDisabled(True)
        self.delete_button.setDisabled(True)
        self.create_button.setDisabled(True)
        self.distribute_mode_btn.setDisabled(True)

        self.label_dropdown = QComboBox()
        self.label_dropdown.setFixedWidth(200)

        self.warning_label = QLabel("⚠️ No annotations for this image")
        self.warning_label.setObjectName("warning")
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.hide()

        self.prev_button = QPushButton("⬅ Previous")
        self.next_button = QPushButton("Next ➡")
        self.prev_button.setDisabled(True)
        self.next_button.setDisabled(True)

        self.labels_layout = QVBoxLayout()
        self.labels_header = QLabel("<b><u>Labels in Image</u></b>")
        self.labels_layout.addWidget(self.labels_header)
        self.labels_layout.addStretch()

        labels_widget = QWidget()
        labels_widget.setLayout(self.labels_layout)

        labels_scroll = QScrollArea()
        labels_scroll.setWidgetResizable(True)
        labels_scroll.setWidget(labels_widget)
        labels_scroll.setFrameShape(QFrame.NoFrame)

        controls_container = QWidget()
        self.controls_layout = QVBoxLayout(controls_container)
        self.controls_layout.setAlignment(Qt.AlignTop)
        self.controls_layout.addWidget(self.label_dropdown)
        self.controls_layout.addSpacing(12)
        self.controls_layout.addWidget(self.create_button)
        self.controls_layout.addWidget(self.delete_button)
        self.controls_layout.addSpacing(20)
        self.controls_layout.addWidget(self.distribute_mode_btn)
        self.controls_layout.addWidget(self.spacing_input)
        self.controls_layout.addWidget(self.apply_dist_btn)
        self.controls_layout.addStretch()

        self.legend_layout = QVBoxLayout()
        self.legend_layout.addWidget(labels_scroll, 1)    
        self.legend_layout.addWidget(controls_container, 0) 

        legend_frame = QFrame()
        legend_frame.setLayout(self.legend_layout)
        legend_frame.setFrameShape(QFrame.StyledPanel)
        legend_frame.setFixedWidth(260)

        top = QHBoxLayout()
        top.addWidget(self.select_button)
        top.addStretch()
        top.addWidget(self.close_button)

        nav = QHBoxLayout()
        nav.addStretch()
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.save_button)
        nav.addStretch()

        center = QHBoxLayout()
        center.addWidget(self.image_view, 1)
        center.addWidget(legend_frame)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.warning_label)
        layout.addLayout(center, 1)
        layout.addLayout(nav)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.select_button.clicked.connect(self.select_folder)
        self.create_button.clicked.connect(self.start_annotation)
        self.delete_button.clicked.connect(self.delete_selected)
        self.save_button.clicked.connect(self.save_annotation)
        self.prev_button.clicked.connect(self.prev_image)
        self.next_button.clicked.connect(self.next_image)
        self.close_button.clicked.connect(self.close)
        
        self.distribute_mode_btn.clicked.connect(self.toggle_distribution_mode)
        self.apply_dist_btn.clicked.connect(self.apply_horizontal_distribution)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder: return
        self.image_folder = folder
        self.load_images()
        self.load_annotations_from_file()
        self.load_task_colors()
        if self.image_files:
            self.current_index = 0
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(True)
            self.create_button.setEnabled(True)
            self.distribute_mode_btn.setEnabled(True)
            self.load_current_image()

    def load_images(self):
        self.image_files = sorted([f for f in os.listdir(self.image_folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))])

    def load_annotations_from_file(self):
        path = os.path.join(self.image_folder, "annotations.json")
        if not os.path.exists(path):
            self.annotations = []
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.annotations = data[0].get("shapes", []) if data else []
        except: self.annotations = []

    def load_task_colors(self):
        self.label_colors.clear()
        self.label_dropdown.clear()
        path = os.path.join(self.image_folder, "task.json")
        if not os.path.exists(path): return
        with open(path, "r") as f:
            data = json.load(f)
        for label in data.get("labels", []):
            self.label_colors[label["name"]] = QColor(label["color"])
            self.label_dropdown.addItem(label["name"])

    def clear_legend(self):
        while self.labels_layout.count() > 1:
            item = self.labels_layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
        self.labels_layout.addStretch()

    def update_legend(self):
        self.clear_legend()
        labels_in_image = sorted(list(set(
            ann["label"] for ann in self.annotations if ann["frame"] == self.current_frame
        )))
        for label in labels_in_image:
            if label not in self.visible_labels:
                self.visible_labels.add(label)
            
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            cb = QCheckBox(label)
            cb.setChecked(label in self.visible_labels)
            color = self.label_colors.get(label, QColor("black")).name()
            cb.setStyleSheet(f"color: {color}; font-weight: bold;")
            cb.toggled.connect(lambda checked, l=label: self.toggle_label_visibility(l, checked))
            
            del_btn = QPushButton("X")
            del_btn.setProperty("class", "delete-label-btn")
            del_btn.setFixedSize(22, 22)
            del_btn.clicked.connect(lambda _, l=label: self.delete_all_of_label(l))
            
            row_layout.addWidget(cb, 1)
            row_layout.addWidget(del_btn, 0)
            
            self.labels_layout.insertWidget(self.labels_layout.count() - 1, row_widget)

    def toggle_label_visibility(self, label, is_checked):
        if is_checked: self.visible_labels.add(label)
        else: self.visible_labels.discard(label)
        self.draw_annotations()

    def draw_annotations(self):
        for item in self.image_view.scene.items():
            if isinstance(item, QGraphicsRectItem) and item != self.image_view.image_item:
                self.image_view.scene.removeItem(item)

        has_data = False
        for ann in self.annotations:
            if ann["frame"] == self.current_frame:
                has_data = True
                label = ann["label"]
                if label in self.visible_labels:
                    x1, y1, x2, y2 = ann["points"]
                    rect = QGraphicsRectItem(0, 0, x2 - x1, y2 - y1)
                    rect.setPos(x1, y1)
                    rect.setPen(QPen(self.label_colors.get(label, QColor("red")), 4))
                    rect.setFlags(QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemSendsGeometryChanges)
                    rect.annotation_ref = ann
                    self.image_view.scene.addItem(rect)
        self.warning_label.setVisible(not has_data)

    def toggle_distribution_mode(self):
        is_active = self.distribute_mode_btn.isChecked()
        self.image_view.is_distribution_mode = is_active
        
        self.create_button.setDisabled(is_active)
        self.delete_button.setDisabled(is_active)
        self.save_button.setDisabled(is_active)
        self.prev_button.setDisabled(is_active)
        self.next_button.setDisabled(is_active)
        self.select_button.setDisabled(is_active)
        
        self.spacing_input.setVisible(is_active)
        self.apply_dist_btn.setVisible(is_active)
        
        if is_active:
            self.distribute_mode_btn.setText("Cancel")
            self.image_view.setCursor(Qt.CrossCursor)
        else:
            self.exit_distribution_mode()

    def exit_distribution_mode(self):
        self.distribute_mode_btn.setChecked(False)
        self.distribute_mode_btn.setText("↔ Distribute Mode")
        self.image_view.is_distribution_mode = False
        self.image_view.unsetCursor()
        
        self.create_button.setEnabled(True)
        self.prev_button.setEnabled(True)
        self.next_button.setEnabled(True)
        self.select_button.setEnabled(True)
        
        self.spacing_input.hide()
        self.apply_dist_btn.hide()
        self.image_view.scene.clearSelection()

    def apply_horizontal_distribution(self):
        selected_items = [item for item in self.image_view.scene.selectedItems() 
                         if isinstance(item, QGraphicsRectItem) and hasattr(item, 'annotation_ref')]
        
        if len(selected_items) < 2:
            return

        try:
            spacing = float(self.spacing_input.currentText())
        except ValueError:
            spacing = 0.0

        selected_items.sort(key=lambda x: x.pos().x() + x.rect().left())
        anchor_y = selected_items[0].pos().y() + selected_items[0].rect().top()
        
        current_x = selected_items[0].pos().x() + selected_items[0].rect().left()
        
        for item in selected_items:
            rect = item.rect()
            
            new_x1 = current_x
            new_y1 = anchor_y
            new_x2 = current_x + rect.width()
            new_y2 = anchor_y + rect.height()
            
            item.annotation_ref["points"] = [int(new_x1), int(new_y1), int(new_x2), int(new_y2)]
            
            current_x = new_x2 + spacing

        self.save_to_json()
        self.exit_distribution_mode()
        self.draw_annotations()

    def load_current_image(self):
        if not self.image_files: return
        filename = self.image_files[self.current_index]
        self.current_frame = extract_frame_number(filename)
        self.image_view.load_image(os.path.join(self.image_folder, filename))
        self.update_legend()
        self.draw_annotations()

    def save_annotation(self):
        rect_item = self.image_view.temp_rect
        if rect_item and not self.image_view.is_distribution_mode:
            r = rect_item.rect()
            if r.width() > 1 and r.height() > 1:
                self.annotations.append({
                    "frame": self.current_frame,
                    "label": self.image_view.current_label,
                    "points": [int(r.left()), int(r.top()), int(r.right()), int(r.bottom())]
                })

        for item in self.image_view.scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, 'annotation_ref'):
                pos = item.pos()
                rect = item.rect()
                item.annotation_ref["points"] = [
                    int(pos.x() + rect.left()), int(pos.y() + rect.top()),
                    int(pos.x() + rect.right()), int(pos.y() + rect.bottom())
                ]

        self.save_to_json()
        self.image_view.disable_drawing()
        self.save_button.setDisabled(True)
        self.update_legend() 
        self.draw_annotations()

    def save_to_json(self):
        if not self.image_folder: return
        path = os.path.join(self.image_folder, "annotations.json")
        with open(path, "w") as f:
            json.dump([{"shapes": self.annotations}], f, indent=2)

    def delete_selected(self):
        selected = self.image_view.scene.selectedItems()
        for item in selected:
            if hasattr(item, 'annotation_ref'):
                self.annotations.remove(item.annotation_ref)
        self.save_to_json()
        self.update_legend() 
        self.draw_annotations()

    def delete_all_of_label(self, label_to_remove):
        self.annotations = [a for a in self.annotations if not (a["frame"] == self.current_frame and a["label"] == label_to_remove)]
        self.save_to_json()
        self.update_legend()
        self.draw_annotations()

    def start_annotation(self):
        label = self.label_dropdown.currentText()
        if not label: return
        self.image_view.enable_drawing(label, self.label_colors.get(label, QColor("red")))
        self.save_button.setEnabled(True)

    def on_selection_changed(self):
        if not self.image_view.is_distribution_mode:
            self.delete_button.setEnabled(bool(self.image_view.scene.selectedItems()))

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_current_image()

    def paste_annotation(self):
        if not self.clipboard_data: return
        new_points = [p + 15 for p in self.clipboard_data["points"]]
        self.annotations.append({
            "frame": self.current_frame,
            "label": self.clipboard_data["label"],
            "points": new_points
        })
        self.save_to_json()
        self.update_legend()
        self.draw_annotations()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())