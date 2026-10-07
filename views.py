import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from constants import SAMPLE_RATE
from data_utils import build_runs, group_entries_by_lead, label_color, lead_sort_key, normalize_lead_name


ECG_SMALL_SQUARE_SECONDS = 0.04
ECG_BIG_SQUARE_SECONDS = 0.2


def draw_grid(scene, rect, sample_length, horizontal_steps):
    minor_pen = QPen(QColor("#f5d5d5"))
    minor_pen.setWidthF(0.9)
    major_pen = QPen(QColor("#df9b9b"))
    major_pen.setWidthF(1.35)

    total_seconds = sample_length / SAMPLE_RATE if sample_length else 0
    total_small_steps = 0
    if total_seconds > 0:
        total_small_steps = int(math.ceil(total_seconds / ECG_SMALL_SQUARE_SECONDS))
        for step in range(total_small_steps + 1):
            time_offset = min(step * ECG_SMALL_SQUARE_SECONDS, total_seconds)
            x = rect.left() + rect.width() * (time_offset / total_seconds)
            is_major = step % int(round(ECG_BIG_SQUARE_SECONDS / ECG_SMALL_SQUARE_SECONDS)) == 0
            scene.addLine(x, rect.top(), x, rect.bottom(), major_pen if is_major else minor_pen)

    if horizontal_steps <= 0 and total_small_steps > 0:
        small_square_height = rect.width() / total_small_steps
        horizontal_steps = max(1, int(round(rect.height() / small_square_height)))

    for step in range(horizontal_steps + 1):
        y = rect.top() + rect.height() * step / horizontal_steps
        is_major = step % int(round(ECG_BIG_SQUARE_SECONDS / ECG_SMALL_SQUARE_SECONDS)) == 0
        scene.addLine(rect.left(), y, rect.right(), y, major_pen if is_major else minor_pen)


def draw_label_spans(scene, rect, sample_length, entries):
    if not sample_length:
        return

    for entry in entries:
        color = label_color(entry.get("label", "unknown"))
        fill = QColor(color)
        fill.setAlpha(95)
        pen = QPen(color)
        pen.setWidthF(1.0)
        brush = QBrush(fill)

        for start, end in build_runs(entry.get("positions", [])):
            x1 = rect.left() + rect.width() * start / sample_length
            x2 = rect.left() + rect.width() * (end + 1) / sample_length
            scene.addRect(QRectF(x1, rect.top(), max(1.0, x2 - x1), rect.height()), pen, brush)


def draw_waveform(scene, rect, signal, sample_length):
    if sample_length <= 1:
        return

    max_abs = max(abs(float(signal.min())), abs(float(signal.max())), 1e-6)
    y_center = rect.center().y()
    amplitude_scale = (rect.height() * 0.42) / max_abs

    path = QPainterPath()
    path.moveTo(rect.left(), y_center - float(signal[0]) * amplitude_scale)
    x_scale = rect.width() / (sample_length - 1)
    for index, value in enumerate(signal[1:], start=1):
        x = rect.left() + index * x_scale
        y = y_center - float(value) * amplitude_scale
        path.lineTo(x, y)

    line_pen = QPen(QColor("#203040"))
    line_pen.setWidthF(1.2)
    scene.addPath(path, line_pen)

    baseline_pen = QPen(QColor("#96a0aa"))
    baseline_pen.setWidthF(0.8)
    scene.addLine(rect.left(), y_center, rect.right(), y_center, baseline_pen)


def add_time_ticks(scene, rect, sample_length):
    if not sample_length:
        return

    seconds = sample_length / SAMPLE_RATE
    tick_pen = QPen(QColor("#a1acb8"))
    label_color_qt = QColor("#4f5d6b")
    whole_seconds = max(1, math.ceil(seconds))

    for second in range(whole_seconds + 1):
        x = rect.left() + rect.width() * min(second / seconds, 1.0) if seconds else rect.left()
        scene.addLine(x, rect.bottom(), x, rect.bottom() + 6, tick_pen)
        label = scene.addText(f"{second:.0f}s")
        label.setDefaultTextColor(label_color_qt)
        label.setPos(x - 10, rect.bottom() + 8)


class LeadOverviewView(QGraphicsView):
    def __init__(self, on_lead_clicked):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.on_lead_clicked = on_lead_clicked
        self.panel_regions = []
        self.sample_bundle = None
        self.setBackgroundBrush(QBrush(QColor("#fbfcfe")))

    def fit_to_width(self):
        rect = self.scene.sceneRect()
        if rect.width() <= 0 or rect.height() <= 0:
            return
        viewport_width = max(1, self.viewport().width() - 4)
        viewport_height = max(1, self.viewport().height() - 4)
        self.resetTransform()
        scale = min(viewport_width / rect.width(), viewport_height / rect.height())
        self.scale(scale, scale)
        self.centerOn(rect.center())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.sample_bundle is not None:
            self.draw_sample(*self.sample_bundle)
        else:
            self.fit_to_width()

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        for rect, lead_name in self.panel_regions:
            if rect.contains(scene_pos):
                self.on_lead_clicked(lead_name)
                event.accept()
                return
        super().mousePressEvent(event)

    def draw_sample(self, sample_data, signal_data, signal_leads, visible_labels=None):
        self.sample_bundle = (sample_data, signal_data, signal_leads, visible_labels)
        self.scene.clear()
        self.panel_regions = []

        if signal_data is None or not signal_leads:
            self.scene.setSceneRect(0, 0, 1000, 300)
            self.fit_to_width()
            return

        sample_length = len(signal_data)
        entries = sample_data.get("entries", [])
        if visible_labels is not None:
            entries = [entry for entry in entries if entry.get("label") in visible_labels]
        entries_by_lead = group_entries_by_lead(entries)
        ordered_pairs = sorted(
            enumerate(signal_leads),
            key=lambda item: lead_sort_key(normalize_lead_name(item[1])),
        )

        columns = 2
        panel_width = 1020
        outer_margin = 0
        column_gap = 0
        row_gap = 0
        title_color = QColor("#1d2a38")

        rows = math.ceil(len(ordered_pairs) / columns)
        scene_width = outer_margin * 2 + columns * panel_width + column_gap
        viewport_width = max(1, self.viewport().width() - 4)
        viewport_height = max(1, self.viewport().height() - 4)
        panel_height = max(90, scene_width * viewport_height / viewport_width / rows)
        scene_height = outer_margin * 2 + rows * panel_height + (rows - 1) * row_gap

        for visual_index, (signal_index, raw_lead_name) in enumerate(ordered_pairs):
            column = visual_index // rows
            row = visual_index % rows
            x = outer_margin + column * (panel_width + column_gap)
            y = outer_margin + row * (panel_height + row_gap)
            panel_rect = QRectF(x, y, panel_width, panel_height)
            plot_rect = QRectF(x + 24, y + 40, panel_width - 48, panel_height - 82)
            lead_name = normalize_lead_name(raw_lead_name)
            signal = signal_data[:, signal_index]
            lead_entries = entries_by_lead.get(lead_name, [])

            self.scene.addRect(panel_rect, QPen(QColor("#d7dde5")), QBrush(QColor("#fbfcfe")))
            self.panel_regions.append((panel_rect, lead_name))

            title = self.scene.addText(lead_name)
            title.setDefaultTextColor(title_color)
            title_font = title.font()
            title_font.setBold(True)
            title.setFont(title_font)
            title.setScale(1.6)
            title.setPos(x + 12, y + 2)

            self.scene.addRect(plot_rect, QPen(Qt.NoPen), QBrush(QColor("white")))
            draw_grid(self.scene, plot_rect, sample_length, horizontal_steps=0)
            draw_label_spans(self.scene, plot_rect, sample_length, lead_entries)
            draw_waveform(self.scene, plot_rect, signal, sample_length)
            add_time_ticks(self.scene, plot_rect, sample_length)

        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self.fit_to_width()


class LeadDetailView(QGraphicsView):
    def __init__(self, on_span_selected, on_span_changed, on_create_box, on_measurement_changed):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.on_span_selected = on_span_selected
        self.on_span_changed = on_span_changed
        self.on_create_box = on_create_box
        self.on_measurement_changed = on_measurement_changed
        self.plot_rect = QRectF()
        self.sample_length = 0
        self.span_items = []
        self.selected_span = None
        self.resize_state = None
        self.move_state = None
        self.press_state = None
        self.create_mode = False
        self.create_label = None
        self.create_start = None
        self.create_preview = None
        self.measure_mode = False
        self.measure_points = []
        self.measurement_items = []
        self.base_scale = 1.0
        self.zoom_factor = 1.0
        self.min_zoom_factor = 1.0
        self.max_zoom_factor = 8.0

    def fit_to_width(self):
        rect = self.scene.sceneRect()
        if rect.width() <= 0:
            return
        viewport_width = max(1, self.viewport().width() - 4)
        self.base_scale = viewport_width / rect.width()
        self.apply_zoom_transform()

    def apply_zoom_transform(self, focus_scene_pos=None):
        rect = self.scene.sceneRect()
        if rect.width() <= 0:
            return
        self.resetTransform()
        scale = self.base_scale * self.zoom_factor
        self.scale(scale, scale)
        self.centerOn(focus_scene_pos if focus_scene_pos is not None else rect.center())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return

        step = 1.15 if delta > 0 else 1 / 1.15
        new_zoom_factor = min(self.max_zoom_factor, max(self.min_zoom_factor, self.zoom_factor * step))
        if math.isclose(new_zoom_factor, self.zoom_factor, rel_tol=1e-6):
            event.accept()
            return

        focus_scene_pos = self.mapToScene(event.position().toPoint())
        self.zoom_factor = new_zoom_factor
        self.apply_zoom_transform(focus_scene_pos)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_width()

    def clear_selection(self):
        self.selected_span = None
        self.resize_state = None
        self.move_state = None
        self.press_state = None
        self.refresh_span_styles()
        self.on_span_selected(None)

    def clear_measurement(self):
        self.measure_points = []
        for item in self.measurement_items:
            self.scene.removeItem(item)
        self.measurement_items = []
        self.on_measurement_changed("")

    def set_measure_mode(self, enabled):
        self.measure_mode = enabled
        self.clear_measurement()
        if enabled:
            self.create_mode = False

    def render_measurement(self):
        for item in self.measurement_items:
            self.scene.removeItem(item)
        self.measurement_items = []

        if not self.measure_points:
            self.on_measurement_changed("")
            return

        marker_pen = QPen(QColor("#8b1e3f"))
        marker_pen.setWidthF(1.6)
        measure_pen = QPen(QColor("#8b1e3f"))
        measure_pen.setWidthF(1.8)
        measure_pen.setStyle(Qt.DashLine)
        text_color = QColor("#8b1e3f")

        for sample_index in self.measure_points:
            x = self.plot_rect.left() + self.plot_rect.width() * sample_index / max(1, self.sample_length - 1)
            line = self.scene.addLine(x, self.plot_rect.top(), x, self.plot_rect.bottom(), marker_pen)
            line.setZValue(4)
            self.measurement_items.append(line)

        if len(self.measure_points) == 2:
            start_sample, end_sample = sorted(self.measure_points)
            x1 = self.plot_rect.left() + self.plot_rect.width() * start_sample / max(1, self.sample_length - 1)
            x2 = self.plot_rect.left() + self.plot_rect.width() * end_sample / max(1, self.sample_length - 1)
            y = self.plot_rect.top() + 18
            line = self.scene.addLine(x1, y, x2, y, measure_pen)
            line.setZValue(4)
            self.measurement_items.append(line)

            delta_seconds = abs(end_sample - start_sample) / SAMPLE_RATE
            midpoint = (x1 + x2) / 2
            label = self.scene.addText(f"dt = {delta_seconds:.3f}s")
            label.setDefaultTextColor(text_color)
            label.setScale(1.0)
            label_rect = label.boundingRect()
            label.setPos(midpoint - label_rect.width() / 2, self.plot_rect.top() - 28)
            label.setZValue(5)
            self.measurement_items.append(label)

            self.on_measurement_changed(
                f"t1 = {start_sample / SAMPLE_RATE:.3f}s, "
                f"t2 = {end_sample / SAMPLE_RATE:.3f}s, "
                f"dt = {delta_seconds:.3f}s"
            )
        else:
            sample_index = self.measure_points[0]
            self.on_measurement_changed(f"t1 = {sample_index / SAMPLE_RATE:.3f}s")

    def refresh_span_styles(self):
        for item in self.span_items:
            color = item["color"]
            fill = QColor(color)
            fill.setAlpha(170 if item is self.selected_span else 110)
            pen = QPen(color)
            pen.setWidthF(2.2 if item is self.selected_span else 1.0)
            item["rect_item"].setBrush(QBrush(fill))
            item["rect_item"].setPen(pen)

    def span_at_pos(self, scene_pos):
        for item in reversed(self.span_items):
            if item["rect"].contains(scene_pos):
                return item
        return None

    def edge_hit(self, item, scene_pos):
        margin = 10
        if abs(scene_pos.x() - item["rect"].left()) <= margin:
            return "left"
        if abs(scene_pos.x() - item["rect"].right()) <= margin:
            return "right"
        return None

    def sample_from_x(self, x_pos):
        if self.sample_length <= 1 or self.plot_rect.width() <= 0:
            return 0
        ratio = (x_pos - self.plot_rect.left()) / self.plot_rect.width()
        ratio = min(1.0, max(0.0, ratio))
        return int(round(ratio * (self.sample_length - 1)))

    def set_create_mode(self, enabled, disease_name=None):
        self.create_mode = enabled
        self.create_label = disease_name
        self.create_start = None
        if enabled:
            self.measure_mode = False
            self.clear_measurement()
        if self.create_preview is not None:
            self.scene.removeItem(self.create_preview)
            self.create_preview = None

    def update_create_preview(self, start_sample, end_sample):
        start = min(start_sample, end_sample)
        end = max(start_sample, end_sample)
        x1 = self.plot_rect.left() + self.plot_rect.width() * start / self.sample_length
        x2 = self.plot_rect.left() + self.plot_rect.width() * (end + 1) / self.sample_length
        rect = QRectF(x1, self.plot_rect.top(), max(1.0, x2 - x1), self.plot_rect.height())
        preview_color = label_color(self.create_label or "")
        pen = QPen(preview_color)
        pen.setStyle(Qt.DashLine)
        brush = QBrush(QColor(preview_color.red(), preview_color.green(), preview_color.blue(), 70))
        if self.create_preview is None:
            self.create_preview = self.scene.addRect(rect, pen, brush)
            self.create_preview.setZValue(2)
        else:
            self.create_preview.setRect(rect)
            self.create_preview.setPen(pen)
            self.create_preview.setBrush(brush)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        if self.measure_mode and self.plot_rect.contains(scene_pos):
            sample_index = self.sample_from_x(scene_pos.x())
            if len(self.measure_points) == 2:
                self.measure_points = [sample_index]
            else:
                self.measure_points.append(sample_index)
            self.clear_selection()
            self.render_measurement()
            event.accept()
            return
        if self.create_mode and self.plot_rect.contains(scene_pos):
            self.create_start = self.sample_from_x(scene_pos.x())
            self.update_create_preview(self.create_start, self.create_start)
            event.accept()
            return
        item = self.span_at_pos(scene_pos)
        if item is not None:
            self.selected_span = item
            edge = self.edge_hit(item, scene_pos)
            if edge is not None:
                self.resize_state = {"item": item, "edge": edge}
                self.move_state = None
                self.press_state = None
            else:
                self.resize_state = None
                self.move_state = None
                self.press_state = {
                    "item": item,
                    "press_x": scene_pos.x(),
                    "press_sample": self.sample_from_x(scene_pos.x()),
                    "start": item["start"],
                    "end": item["end"],
                }
            self.refresh_span_styles()
            self.on_span_selected(item)
            event.accept()
            return
        self.clear_selection()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.create_mode and self.create_start is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            current_sample = self.sample_from_x(scene_pos.x())
            self.update_create_preview(self.create_start, current_sample)
            event.accept()
            return
        if self.resize_state is None and self.move_state is None and self.press_state is None:
            super().mouseMoveEvent(event)
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        if self.press_state is not None:
            if abs(scene_pos.x() - self.press_state["press_x"]) > 8:
                self.move_state = self.press_state
                self.press_state = None
            else:
                event.accept()
                return

        if self.resize_state is not None:
            item = self.resize_state["item"]
            new_sample = self.sample_from_x(scene_pos.x())
            start = item["start"]
            end = item["end"]

            if self.resize_state["edge"] == "left":
                start = max(0, min(new_sample, end - 1))
            else:
                end = min(self.sample_length - 1, max(new_sample, start + 1))
        else:
            item = self.move_state["item"]
            new_sample = self.sample_from_x(scene_pos.x())
            width = self.move_state["end"] - self.move_state["start"]
            delta = new_sample - self.move_state["press_sample"]
            start = self.move_state["start"] + delta
            end = self.move_state["end"] + delta
            if start < 0:
                end -= start
                start = 0
            if end > self.sample_length - 1:
                shift = end - (self.sample_length - 1)
                start -= shift
                end = self.sample_length - 1
            if end <= start:
                end = min(self.sample_length - 1, start + max(1, width))

        item["start"] = start
        item["end"] = end
        x1 = self.plot_rect.left() + self.plot_rect.width() * start / self.sample_length
        x2 = self.plot_rect.left() + self.plot_rect.width() * (end + 1) / self.sample_length
        rect = QRectF(x1, self.plot_rect.top(), max(1.0, x2 - x1), self.plot_rect.height())
        item["rect"] = rect
        item["rect_item"].setRect(rect)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.create_mode and self.create_start is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            end_sample = self.sample_from_x(scene_pos.x())
            start = min(self.create_start, end_sample)
            end = max(self.create_start, end_sample)
            self.create_start = None
            if self.create_preview is not None:
                self.scene.removeItem(self.create_preview)
                self.create_preview = None
            self.create_mode = False
            if end > start:
                self.on_create_box(self.create_label, start, end)
            event.accept()
            return
        if self.press_state is not None:
            self.press_state = None
            event.accept()
            return
        if self.resize_state is not None or self.move_state is not None:
            changed_item = self.resize_state["item"] if self.resize_state is not None else self.move_state["item"]
            self.resize_state = None
            self.move_state = None
            self.on_span_changed(changed_item)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def draw_lead(self, sample_id, lead_name, signal, entries, visible_labels=None):
        self.scene.clear()
        self.span_items = []
        self.selected_span = None
        self.resize_state = None
        self.move_state = None
        self.press_state = None

        sample_length = len(signal)
        self.sample_length = sample_length
        scene_rect = QRectF(0, 0, 1650, 760)
        plot_rect = QRectF(40, 72, 1570, 540)
        self.plot_rect = plot_rect
        self.scene.addRect(scene_rect, QPen(Qt.NoPen), QBrush(QColor("#f7f9fc")))

        title = self.scene.addText(f"Lead {lead_name}")
        title.setDefaultTextColor(QColor("#1d2a38"))
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        title.setScale(1.7)
        title_rect = title.boundingRect()
        title.setPos((scene_rect.width() - title_rect.width() * title.scale()) / 2, 18)

        self.scene.addRect(plot_rect, QPen(QColor("#ccd4dd")), QBrush(QColor("white")))
        draw_grid(self.scene, plot_rect, sample_length, horizontal_steps=0)
        filtered_entries = entries
        if visible_labels is not None:
            filtered_entries = [entry for entry in entries if entry.get("label") in visible_labels]

        for entry in filtered_entries:
            color = label_color(entry.get("label", "unknown"))
            for run_index, (start, end) in enumerate(build_runs(entry.get("positions", []))):
                x1 = plot_rect.left() + plot_rect.width() * start / sample_length
                x2 = plot_rect.left() + plot_rect.width() * (end + 1) / sample_length
                rect = QRectF(x1, plot_rect.top(), max(1.0, x2 - x1), plot_rect.height())
                rect_item = self.scene.addRect(rect, QPen(color), QBrush(QColor(color.red(), color.green(), color.blue(), 110)))
                rect_item.setZValue(1)
                self.span_items.append(
                    {
                        "rect_item": rect_item,
                        "rect": rect,
                        "entry": entry,
                        "run_index": run_index,
                        "label": entry.get("label", "unknown"),
                        "color": color,
                        "start": start,
                        "end": end,
                    }
                )
        draw_waveform(self.scene, plot_rect, signal, sample_length)
        add_time_ticks(self.scene, plot_rect, sample_length)

        text_y = 640
        if filtered_entries:
            for entry in filtered_entries:
                color = label_color(entry.get("label", "unknown"))
                runs = build_runs(entry.get("positions", []))
                ranges = ", ".join(f"{start / SAMPLE_RATE:.2f}-{(end + 1) / SAMPLE_RATE:.2f}s" for start, end in runs[:6])
                if len(runs) > 6:
                    ranges += ", ..."
                item = self.scene.addText(f"{entry.get('label', 'unknown')}: {ranges}")
                item.setDefaultTextColor(color)
                item.setScale(1.08)
                item.setPos(70, text_y)
                text_y += 28
        else:
            item = self.scene.addText("No visible labels for this lead.")
            item.setDefaultTextColor(QColor("#607080"))
            item.setScale(1.08)
            item.setPos(70, text_y)

        self.refresh_span_styles()
        self.render_measurement()
        self.on_span_selected(None)
        self.scene.setSceneRect(scene_rect)
        self.fit_to_width()
