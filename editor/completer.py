from __future__ import annotations

from dataclasses import dataclass
import builtins
import inspect
import json
import keyword
import os
import re
import types
from collections import deque
from difflib import get_close_matches
from typing import List, Sequence, Tuple

from PySide2.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QSize, Qt, QTimer
from PySide2.QtGui import QColor, QFont, QFontMetrics, QPainter, QTextCursor
from PySide2.QtWidgets import QApplication, QCompleter, QLabel, QListView, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from editor.core import CodeEditorSettings, PathFromOS

try:
    import nuke
except ImportError:  # pragma: no cover
    nuke = None
try:
    import nukescripts  # type: ignore
except Exception:  # pragma: no cover
    nukescripts = None
try:
    from PySide2 import QtCore as _QtCore
    from PySide2 import QtGui as _QtGui
    from PySide2 import QtWidgets as _QtWidgets
except Exception:  # pragma: no cover
    _QtCore = None
    _QtGui = None
    _QtWidgets = None


class CompletionRole:
    TEXT = Qt.UserRole + 1
    KIND = Qt.UserRole + 2
    SOURCE = Qt.UserRole + 3
    SCORE = Qt.UserRole + 4
    MATCH_PREFIX = Qt.UserRole + 5
    MATCH_INDICES = Qt.UserRole + 6
    INFO = Qt.UserRole + 7


@dataclass(frozen=True)
class CompletionItem:
    text: str
    kind: str
    source: str
    score: float
    match_prefix: str = ""
    match_indices: Tuple[int, ...] = ()
    info: str = ""


class CompletionListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[CompletionItem] = []

    def rowCount(self, parent=QModelIndex()):  # noqa: N802 (Qt API)
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: N802 (Qt API)
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        item = self._items[row]

        if role in (Qt.DisplayRole, CompletionRole.TEXT):
            return item.text
        if role == CompletionRole.KIND:
            return item.kind
        if role == CompletionRole.SOURCE:
            return item.source
        if role == CompletionRole.SCORE:
            return item.score
        if role == CompletionRole.MATCH_PREFIX:
            return item.match_prefix
        if role == CompletionRole.MATCH_INDICES:
            return item.match_indices
        if role == CompletionRole.INFO:
            return item.info
        return None

    def set_items(self, items: Sequence[CompletionItem]):
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()


class CompletionItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._text_color = QColor("#d4d4d4")
        self._selected_text_color = QColor("#ffffff")
        self._hover_bg = QColor("#2a2d2e")
        self._selected_bg = QColor("#094771")
        self._source_color = QColor("#9aa0a6")
        self._nuke_orange = QColor("#f18f01")

        self._icon_bg_map = {
            "nuke": QColor("#f18f01"),
            "node": QColor("#f18f01"),
            "builtin": QColor("#2f8f4e"),
            "pyside2": QColor("#7aa9ff"),
            "python": QColor("#a9cce3"),
            "local": QColor("#6c757d"),
        }

        self._kind_glyph = {
            "function": "ƒ",
            "class": "C",
            "module": "M",
            "keyword": "K",
            "decorator": "@",
            "object": "O",
            "node": "N",
            "name": "V",
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):  # noqa: N802 (Qt API)
        text = (index.data(CompletionRole.TEXT) or "").strip()
        if not text:
            return

        kind = (index.data(CompletionRole.KIND) or "name").strip()
        source = (index.data(CompletionRole.SOURCE) or "local").strip()
        match_prefix = (index.data(CompletionRole.MATCH_PREFIX) or "").strip()
        match_indices = index.data(CompletionRole.MATCH_INDICES) or ()
        if not isinstance(match_indices, (tuple, list)):
            match_indices = ()

        is_selected = bool(option.state & QStyle.State_Selected)
        is_hover = bool(option.state & QStyle.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect
        if is_selected:
            painter.fillRect(rect, self._selected_bg)
        elif is_hover:
            painter.fillRect(rect, self._hover_bg)

        padding_x = 8
        icon_size = 14
        icon_gap = 6
        source_gap = 8

        icon_x = rect.x() + padding_x
        icon_y = rect.y() + (rect.height() - icon_size) // 2

        icon_bg = self._icon_bg_map.get(source, QColor("#6c757d"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(icon_bg)
        painter.drawRoundedRect(icon_x, icon_y, icon_size, icon_size, 4, 4)

        glyph = self._kind_glyph.get(kind, "V")
        glyph_font = QFont(option.font)
        glyph_font.setPointSize(max(8, glyph_font.pointSize() - 3))
        glyph_font.setBold(True)
        painter.setFont(glyph_font)
        painter.setPen(QColor("#111111"))
        painter.drawText(icon_x, icon_y, icon_size, icon_size, Qt.AlignCenter, glyph)

        source_font = QFont(option.font)
        source_font.setPointSize(max(9, source_font.pointSize() - 3))
        source_metrics = QFontMetrics(source_font)
        source_text = source
        source_w = source_metrics.horizontalAdvance(source_text)

        right_edge = rect.right() - padding_x
        source_rect_x = right_edge - source_w

        painter.setFont(source_font)
        painter.setPen(self._selected_text_color if is_selected else self._source_color)
        painter.drawText(
            source_rect_x,
            rect.y(),
            source_w,
            rect.height(),
            Qt.AlignVCenter | Qt.AlignRight,
            source_text,
        )

        text_x = icon_x + icon_size + icon_gap
        text_right = source_rect_x - source_gap
        text_w = max(0, text_right - text_x)

        base_font = QFont(option.font)
        painter.setFont(base_font)
        base_metrics = QFontMetrics(base_font)

        elided = base_metrics.elidedText(text, Qt.ElideRight, text_w)

        normal_pen = self._selected_text_color if is_selected else self._text_color
        y = rect.y() + int((rect.height() + base_metrics.ascent() - base_metrics.descent()) / 2)
        x = text_x

        painter.setPen(normal_pen)
        if match_indices and match_prefix:
            # Recompute indices for the elided string to keep highlighting accurate.
            recomputed = self._subsequence_match_indices(match_prefix, elided)
            if recomputed:
                match_indices = recomputed
        self._draw_highlighted_text(
            painter=painter,
            metrics=base_metrics,
            x=x,
            y=y,
            text=elided,
            match_indices=set(int(i) for i in match_indices if isinstance(i, int) and 0 <= i < len(elided)),
            normal_pen=normal_pen,
            highlight_pen=self._nuke_orange,
        )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):  # noqa: N802 (Qt API)
        base = super().sizeHint(option, index)
        height = max(base.height(), QFontMetrics(option.font).height() + 6)
        return QSize(base.width(), height)

    def _draw_highlighted_text(
        self,
        painter: QPainter,
        metrics: QFontMetrics,
        x: int,
        y: int,
        text: str,
        match_indices: set,
        normal_pen: QColor,
        highlight_pen: QColor,
    ):
        if not text:
            return
        if not match_indices:
            painter.setPen(normal_pen)
            painter.drawText(x, y, text)
            return

        run = []
        run_is_highlight = None

        def flush():
            nonlocal x, run, run_is_highlight
            if not run:
                return
            painter.setPen(highlight_pen if run_is_highlight else normal_pen)
            s = "".join(run)
            painter.drawText(x, y, s)
            x += metrics.horizontalAdvance(s)
            run = []

        for i, ch in enumerate(text):
            is_h = i in match_indices
            if run_is_highlight is None:
                run_is_highlight = is_h
            if is_h != run_is_highlight:
                flush()
                run_is_highlight = is_h
            run.append(ch)
        flush()

    def _subsequence_match_indices(self, pattern: str, candidate: str) -> Tuple[int, ...]:
        pattern = (pattern or "").strip()
        candidate = candidate or ""
        if not pattern or not candidate:
            return ()

        p = pattern.lower()
        c = candidate.lower()

        if c.startswith(p):
            return tuple(range(min(len(pattern), len(candidate))))

        if p in c and len(p) >= 2:
            start = c.find(p)
            if start >= 0:
                end = min(len(candidate), start + len(pattern))
                return tuple(range(start, end))

        out: List[int] = []
        pos = 0
        for ch in p:
            idx = c.find(ch, pos)
            if idx < 0:
                return ()
            out.append(idx)
            pos = idx + 1
        return tuple(out)


class CompletionPopupView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setTextElideMode(Qt.ElideRight)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._info_raw = ""
        self.info_line = QLabel(self)
        self.info_line.setFixedHeight(20)
        self.info_line.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_line.setVisible(False)
        self.info_line.setStyleSheet(
            "background-color: #1f1f1f; color: #c9c9c9; padding: 0px 8px; border-top: 1px solid #333333;"
        )

    def set_info_text(self, text: str):
        raw = (text or "").strip()
        self._info_raw = raw
        self.info_line.setVisible(bool(raw))
        if raw:
            self._layout_info_line()
        else:
            self.info_line.setText("")
            self.setViewportMargins(0, 0, 0, 0)

    def resizeEvent(self, event):  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._layout_info_line()

    def _layout_info_line(self):
        if not self.info_line.isVisible():
            return
        h = self.info_line.height()
        self.info_line.setGeometry(0, self.height() - h, self.width(), h)
        self.setViewportMargins(0, 0, 0, h)
        self._update_info_elide()

    def _update_info_elide(self):
        if not self.info_line.isVisible():
            return
        available = max(0, self.info_line.width() - 16)
        elided = self.info_line.fontMetrics().elidedText(self._info_raw, Qt.ElideRight, available)
        if self.info_line.text() != elided:
            self.info_line.setText(elided)


class Completer:
    """
    Popup completion controller (clean baseline).

    This is intentionally minimal: it only computes candidates and shows a popup.
    Rendering (icons, right-side info, highlight) will be added in the next steps.
    """

    def __init__(self, editor):
        self.editor = editor

        self.model = CompletionListModel()
        self.completion_popup = QCompleter(self.model)
        self.completion_popup.setWidget(self.editor)
        self.completion_popup.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completion_popup.setCaseSensitivity(Qt.CaseInsensitive)

        self.popup_view = CompletionPopupView()
        self.popup_view.setModel(self.model)
        self.popup_view.setFont(self._popup_font())
        self.popup_view.setStyleSheet(self._popup_styles())
        self.completion_popup.setPopup(self.popup_view)

        # QCompleter may override the popup's delegate internally; keep our delegate alive
        # and re-apply it whenever we show the popup.
        self._item_delegate = CompletionItemDelegate(self.popup_view)
        self.popup_view.setItemDelegate(self._item_delegate)
        try:
            self.completion_popup.popup().setItemDelegate(self._item_delegate)
        except Exception:
            pass

        self.recent_completions = deque(maxlen=20)
        self._cached_identifiers: List[str] = []
        self._cached_doc_text: str = ""
        self._pyside_index = self._build_pyside_index()
        self._connected_selection = False
        self._active_prefix: str = ""
        self._active_context = None
        self._node_cache: dict = {}
        self._node_loaded = False
        self._debounce_timer = QTimer(self.editor)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._update_completions_now)
        self._debounce_ms = 60

        self.popup_view.entered.connect(self._update_info_from_index)
        self.popup_view.clicked.connect(self._insert_from_index)
        self.popup_view.activated.connect(self._insert_from_index)

    def hide_popup(self):
        try:
            self.completion_popup.popup().hide()
        except Exception:
            pass
        try:
            self.popup_view.set_info_text("")
        except Exception:
            pass
        self._active_prefix = ""
        self._active_context = None
        try:
            self._debounce_timer.stop()
        except Exception:
            pass

    def accept_current(self) -> bool:
        popup = self.completion_popup.popup()
        index = popup.currentIndex()
        if not index.isValid():
            return False
        completion = index.data(Qt.DisplayRole) or ""
        if not completion:
            return False
        self.insert_completion(completion)
        return True

    def update_completions(self, immediate: bool = False):
        settings = CodeEditorSettings()
        if not settings.ENABLE_COMPLETER or not getattr(settings, "ENABLE_COMPLETION_POPUP", True):
            self.hide_popup()
            return
        if immediate:
            self._update_completions_now()
            return
        try:
            self._debounce_timer.start(self._debounce_ms)
        except Exception:
            self._update_completions_now()

    def _update_completions_now(self):
        settings = CodeEditorSettings()
        if not settings.ENABLE_COMPLETER or not getattr(settings, "ENABLE_COMPLETION_POPUP", True):
            self.hide_popup()
            return

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.hide_popup()
            return

        prefix, context = self._get_completion_prefix_and_context(cursor)
        if (not prefix and context is None) or not self.editor.toPlainText().strip():
            self.hide_popup()
            return

        # Suppress in comments/strings except for node-name completion inside createNode("...").
        if hasattr(self.editor, "_cursor_in_string_or_comment"):
            try:
                in_comment, in_string = self.editor._cursor_in_string_or_comment()
                if in_comment:
                    self.hide_popup()
                    return
                if in_string and not (context and context.get("type") == "node_name"):
                    self.hide_popup()
                    return
            except Exception:
                pass

        self._active_prefix = prefix or ""
        self._active_context = context

        items = self._build_items(prefix, context=context)
        if not items:
            self.hide_popup()
            return

        self.model.set_items(items)
        self._ensure_popup_signals()
        try:
            # Keep QCompleter's internal completion model in sync to avoid empty popups.
            self.completion_popup.setCompletionPrefix(prefix or "")
        except Exception:
            pass

        try:
            popup_model = self.completion_popup.popup().model()
            if popup_model is not None and popup_model.rowCount() <= 0:
                self.hide_popup()
                return
        except Exception:
            pass

        # QCompleter can reset delegates when updating; enforce ours.
        try:
            self.completion_popup.popup().setItemDelegate(self._item_delegate)
        except Exception:
            pass

        cr = self.editor.cursorRect()
        cr.translate(35, 5)
        popup_width = self._calculate_popup_width(items)
        cr = self._clamp_rect_to_screen(cr, popup_width)
        self.completion_popup.complete(cr)
        try:
            popup_model = self.completion_popup.popup().model()
            if popup_model is not None and popup_model.rowCount() <= 0:
                self.hide_popup()
                return
        except Exception:
            pass
        self._ensure_first_item_selected()
        self._update_info_from_index(self.completion_popup.popup().currentIndex())

    def insert_completion(self, completion: str):
        cursor = self.editor.textCursor()
        remove_len = len(self._active_prefix or "")
        if remove_len > 0:
            start = max(0, cursor.position() - remove_len)
            cursor.setPosition(start, QTextCursor.MoveAnchor)
            cursor.setPosition(start + remove_len, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
        cursor.insertText(completion)
        self.editor.setTextCursor(cursor)

        if completion not in self.recent_completions:
            self.recent_completions.appendleft(completion)

        self.hide_popup()

    def _insert_from_index(self, index: QModelIndex):
        try:
            if not index.isValid():
                return
            completion = index.data(Qt.DisplayRole) or ""
            if completion:
                self.insert_completion(str(completion))
        except Exception:
            pass

    def _ensure_popup_signals(self):
        if self._connected_selection:
            return
        try:
            sel = self.popup_view.selectionModel()
        except Exception:
            sel = None
        if sel is None:
            return
        sel.currentChanged.connect(lambda current, _prev: self._update_info_from_index(current))
        self._connected_selection = True

    def _update_info_from_index(self, index: QModelIndex):
        try:
            if not index or not index.isValid():
                self.popup_view.set_info_text("")
                return
            info = index.data(CompletionRole.INFO) or ""
            self.popup_view.set_info_text(str(info))
        except Exception:
            try:
                self.popup_view.set_info_text("")
            except Exception:
                pass

    def _ensure_first_item_selected(self):
        popup = self.completion_popup.popup()
        model = popup.model()
        if not model or model.rowCount() <= 0:
            return
        first = model.index(0, 0)
        if first.isValid():
            popup.setCurrentIndex(first)

    def _popup_font(self) -> QFont:
        font = QFont()
        font.setFamily(CodeEditorSettings().main_default_font)
        font.setPointSize(max(9, int(CodeEditorSettings().main_font_size) - 2))
        return font

    def _popup_styles(self) -> str:
        return """
            QListView {
                background-color: #252526;
                color: #d4d4d4;
                padding: 2px 0px;
                border: 1px solid #454545;
                border-radius: 7px;
                outline: 0;
            }
            QListView::item {
                padding: 2px 8px;
            }
            QListView::item:hover {
                background-color: #2a2d2e;
            }
            QListView::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 6px 4px 6px 0px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4f4f4f;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """

    def _calculate_popup_width(self, items: Sequence[CompletionItem]) -> int:
        sample = items[:200] if isinstance(items, list) else list(items)[:200]

        base_font = QFont(self.popup_view.font())
        base_metrics = QFontMetrics(base_font)

        source_font = QFont(base_font)
        source_font.setPointSize(max(9, source_font.pointSize() - 3))
        source_metrics = QFontMetrics(source_font)

        max_text_w = 0
        max_source_w = 0
        for item in sample:
            max_text_w = max(max_text_w, base_metrics.horizontalAdvance(item.text))
            max_source_w = max(max_source_w, source_metrics.horizontalAdvance(item.source))

        padding_x = 8
        icon_size = 14
        icon_gap = 6
        source_gap = 8
        scrollbar_w = self.popup_view.verticalScrollBar().sizeHint().width()

        desired = padding_x + icon_size + icon_gap + max_text_w + source_gap + max_source_w + padding_x + scrollbar_w

        available = QApplication.desktop().availableGeometry(self.editor)
        margin = 12
        max_w = max(280, min(520, available.width() - (margin * 2)))
        return max(280, min(int(desired), int(max_w)))

    def _clamp_rect_to_screen(self, rect: QRect, popup_width: int) -> QRect:
        available = QApplication.desktop().availableGeometry(self.editor)
        margin = 12
        popup_width = min(popup_width, max(280, min(520, available.width() - (margin * 2))))

        anchor_global = self.editor.mapToGlobal(rect.bottomLeft())
        x_global = anchor_global.x()

        if x_global + popup_width + margin > available.right():
            x_global = available.right() - popup_width - margin
        if x_global < available.left() + margin:
            x_global = available.left() + margin

        local_x = self.editor.mapFromGlobal(QPoint(x_global, anchor_global.y())).x()
        rect.moveLeft(local_x)
        rect.setWidth(popup_width)
        return rect

    def _build_items(self, prefix: str, context=None) -> List[CompletionItem]:
        prefix_norm = prefix.lower()

        candidates, base_priority, fixed_source = self._collect_candidates(context=context)
        if not candidates:
            return []

        items: List[CompletionItem] = []
        for text in candidates:
            match_indices, match_score = self._match_indices_and_score(prefix, text)
            if match_score <= 0:
                continue

            if fixed_source is not None:
                kind, source = self._classify_with_source(text, fixed_source, context=context)
            else:
                kind, source = self._classify(text)
            info = self._build_info(text=text, kind=kind, source=source, context=context)
            priority = float(base_priority.get(text, 0))
            recent_boost = 5.0 if text in self.recent_completions else 0.0
            source_boost = 6.0 if source == "nuke" else 2.0 if source == "pyside2" else 0.0
            score = match_score + priority + recent_boost + source_boost
            items.append(
                CompletionItem(
                    text=text,
                    kind=kind,
                    source=source,
                    score=score,
                    match_prefix=prefix,
                    match_indices=match_indices,
                    info=info,
                )
            )

        if CodeEditorSettings().ENABLE_FUZZY_COMPLETION and len(prefix_norm) >= 3 and len(items) < 30:
            normalized_map = {c.lower(): c for c in candidates}
            fuzzy_keys = get_close_matches(prefix_norm, normalized_map.keys(), n=30, cutoff=0.6)
            existing = {it.text for it in items}
            for key in fuzzy_keys:
                text = normalized_map.get(key)
                if not text or text in existing:
                    continue
                if fixed_source is not None:
                    kind, source = self._classify_with_source(text, fixed_source, context=context)
                else:
                    kind, source = self._classify(text)
                info = self._build_info(text=text, kind=kind, source=source, context=context)
                priority = float(base_priority.get(text, 0))
                recent_boost = 5.0 if text in self.recent_completions else 0.0
                source_boost = 6.0 if source == "nuke" else 2.0 if source == "pyside2" else 0.0
                items.append(
                    CompletionItem(
                        text=text,
                        kind=kind,
                        source=source,
                        score=520.0 + priority + recent_boost + source_boost,
                        match_prefix=prefix,
                        match_indices=(),
                        info=info,
                    )
                )
                existing.add(text)

        items.sort(key=lambda item: (-item.score, item.text.lower()))
        return items[:200]

    def _classify_with_source(self, name: str, source: str, context=None) -> Tuple[str, str]:
        if source == "node":
            return "node", "node"
        if context is None:
            return "name", source
        obj = context.get("object")
        if obj is None:
            return "name", source
        try:
            value = getattr(obj, name)
        except Exception:
            return "name", source

        if isinstance(value, type):
            return "class", source
        if callable(value):
            return "function", source
        # Heuristic: treat modules specially
        if hasattr(value, "__spec__") or hasattr(value, "__path__"):
            return "module", source
        return "object", source

    def _build_info(self, text: str, kind: str, source: str, context=None) -> str:
        base = ""
        if context and context.get("type") == "attr":
            base_name = context.get("base") or ""
            if base_name:
                base = f"{base_name}.{text}"

        if source == "node":
            self._ensure_node_cache()
            category = ""
            try:
                category = self._node_cache.get(text, "") if isinstance(self._node_cache, dict) else ""
            except Exception:
                category = ""
            if category:
                return f"Node • {category}"
            return "Node"

        if source == "builtin":
            obj = getattr(builtins, text, None)
            return self._format_object_info(obj, fallback=f"builtins.{text}")
        if source == "python" and kind == "keyword":
            return f"keyword: {text}"
        if source == "nuke":
            obj = None
            if context and context.get("type") == "attr":
                try:
                    obj = getattr(context.get("object"), text)
                except Exception:
                    obj = None
            else:
                try:
                    obj = getattr(nuke, text) if nuke else None
                except Exception:
                    obj = None
            return self._format_object_info(obj, fallback=(base or f"nuke.{text}"))
        if source == "pyside2":
            obj = None
            if context and context.get("type") == "attr":
                try:
                    obj = getattr(context.get("object"), text)
                except Exception:
                    obj = None
                base_name = context.get("base") or ""
                if base_name:
                    return self._format_object_info(obj, fallback=f"{base_name}.{text}")
            return self._format_object_info(obj, fallback=text)
        if source == "local":
            return base or "local"
        return base or source

    def _format_object_info(self, obj, fallback: str) -> str:
        if obj is None:
            return fallback
        try:
            if callable(obj):
                try:
                    sig = str(inspect.signature(obj))
                    return f"{fallback}{sig}"
                except Exception:
                    pass
            doc = getattr(obj, "__doc__", None)
            if doc:
                first = doc.strip().splitlines()[0].strip()
                if first:
                    return first
        except Exception:
            pass
        return fallback

    def _get_completion_prefix_and_context(self, cursor: QTextCursor):
        """
        Returns (prefix, context) where context is a dict when completing attributes:
        - {"type": "attr", "base": "<name>", "object": <python obj>, "source": "<source>"}
        """
        try:
            block_text = cursor.block().text()
            pos = cursor.positionInBlock()
            before = block_text[:pos]

            # Node string completion: nuke.createNode("Blur")
            node_prefix, node_ctx = self._get_create_node_string_context(block_text, pos)
            if node_ctx is not None:
                return node_prefix, node_ctx

            # Node constructors: nuke.nodes.Blur(...)
            m = re.search(r"\bnuke\.nodes\.(\w*)$", before)
            if m and nuke and hasattr(nuke, "nodes"):
                prefix = m.group(1) or ""
                return prefix, {"type": "node_attr", "base": "nuke.nodes", "object": getattr(nuke, "nodes"), "source": "node", "prefix": prefix}

            # Node constructors (common import): nodes.Blur(...)
            m = re.search(r"\bnodes\.(\w*)$", before)
            if m and nuke and hasattr(nuke, "nodes"):
                prefix = m.group(1) or ""
                return prefix, {"type": "node_attr", "base": "nodes", "object": getattr(nuke, "nodes"), "source": "node", "prefix": prefix}

            # PySide2: PySide2.QtWidgets.Q...
            m = re.search(r"\bPySide2\.(QtCore|QtGui|QtWidgets)\.(\w*)$", before)
            if m:
                base = m.group(1)
                prefix = m.group(2) or ""
                obj = {"QtCore": _QtCore, "QtGui": _QtGui, "QtWidgets": _QtWidgets}.get(base)
                if obj:
                    return prefix, {"type": "attr", "base": base, "object": obj, "source": "pyside2", "prefix": prefix}

            # Common aliases: QtWidgets.Q...
            m = re.search(r"\b(QtCore|QtGui|QtWidgets)\.(\w*)$", before)
            if m:
                base = m.group(1)
                prefix = m.group(2) or ""
                obj = {"QtCore": _QtCore, "QtGui": _QtGui, "QtWidgets": _QtWidgets}.get(base)
                if obj:
                    return prefix, {"type": "attr", "base": base, "object": obj, "source": "pyside2", "prefix": prefix}

            # Nuke modules
            m = re.search(r"\b(nuke|nukescripts)\.(\w*)$", before)
            if m:
                base = m.group(1)
                prefix = m.group(2) or ""
                obj = nuke if base == "nuke" else nukescripts
                if obj:
                    return prefix, {"type": "attr", "base": base, "object": obj, "source": "nuke", "prefix": prefix}

        except Exception:
            pass

        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.WordUnderCursor)
        prefix = (word_cursor.selectedText() or "").strip()
        return prefix, None

    def _get_create_node_string_context(self, line_text: str, cursor_pos: int):
        """
        Detects if the cursor is inside the first string argument of nuke.createNode(...).
        Returns (prefix, context) or ("", None).
        """
        if not line_text or cursor_pos <= 0:
            return "", None

        # Find the last 'nuke.createNode(' before the cursor.
        matches = list(re.finditer(r"\bnuke\.createNode\s*\(", line_text))
        if not matches:
            return "", None

        active = None
        for m in matches:
            if m.end() <= cursor_pos:
                active = m
        if active is None:
            return "", None

        i = active.end()
        while i < cursor_pos and line_text[i].isspace():
            i += 1
        if i >= cursor_pos:
            return "", None

        quote = line_text[i]
        if quote not in ("'", '"'):
            return "", None

        # Ensure we are still inside this string (no unescaped closing quote before cursor).
        escaped = False
        j = i + 1
        while j < cursor_pos:
            ch = line_text[j]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                # Cursor is after the closing quote -> not in string.
                return "", None
            j += 1

        raw = line_text[i + 1:cursor_pos]
        m2 = re.search(r"([A-Za-z0-9_]+)$", raw)
        prefix = m2.group(1) if m2 else ""
        return prefix, {"type": "node_name", "source": "node", "prefix": prefix}

    def _classify(self, text: str) -> Tuple[str, str]:
        if text in keyword.kwlist:
            return "keyword", "python"
        if hasattr(builtins, text):
            obj = getattr(builtins, text, None)
            return ("function" if callable(obj) else "object"), "builtin"
        if nuke and hasattr(nuke, text):
            obj = getattr(nuke, text, None)
            return ("function" if callable(obj) else "object"), "nuke"
        if text in self._pyside_index:
            return self._pyside_index[text]
        if text.startswith("@"):
            return "decorator", "python"
        return "name", "local"

    def _build_pyside_index(self) -> dict:
        if not (_QtCore and _QtGui and _QtWidgets):
            return {}
        modules = (_QtCore, _QtGui, _QtWidgets)
        index: dict = {}
        for mod in modules:
            try:
                for name in dir(mod):
                    if not name or name.startswith("_"):
                        continue
                    obj = getattr(mod, name, None)
                    if isinstance(obj, type):
                        kind = "class"
                    elif callable(obj):
                        kind = "function"
                    else:
                        kind = "object"
                    index.setdefault(name, (kind, "pyside2"))
            except Exception:
                continue
        return index

    def _match_indices_and_score(self, pattern: str, candidate: str) -> Tuple[Tuple[int, ...], float]:
        pattern = (pattern or "").strip()
        candidate = (candidate or "").strip()
        if not candidate:
            return (), 0.0
        if not pattern:
            # Used for attribute completion right after a dot (e.g. `nuke.`).
            # Keep a stable ordering but allow everything to show.
            return (), 450.0

        p = pattern.lower()
        c = candidate.lower()

        # Keep auto-popup noise low: for 1-char patterns, only allow prefix matches.
        if len(p) < 2 and not c.startswith(p):
            return (), 0.0

        if c.startswith(p):
            indices = tuple(range(min(len(pattern), len(candidate))))
            return indices, 1000.0

        if len(p) >= 2:
            start = c.find(p)
            if start >= 0:
                end = min(len(candidate), start + len(pattern))
                indices = tuple(range(start, end))
                # Earlier substring matches rank higher.
                return indices, 850.0 - float(start * 2)

        # Subsequence match (harf harf)
        out: List[int] = []
        pos = 0
        for ch in p:
            idx = c.find(ch, pos)
            if idx < 0:
                return (), 0.0
            out.append(idx)
            pos = idx + 1

        if not out:
            return (), 0.0

        span = out[-1] - out[0] + 1
        gaps = span - len(p)
        start_penalty = out[0] * 2
        gap_penalty = gaps * 6
        base_score = 700.0 - float(start_penalty + gap_penalty)

        # CamelCase / abbreviation boosting (PyCharm-like feel)
        boundaries = {0}
        for i in range(1, len(candidate)):
            prev = candidate[i - 1]
            cur = candidate[i]
            nxt = candidate[i + 1] if i + 1 < len(candidate) else ""
            if prev in "._-/\\ ":
                boundaries.add(i)
            elif prev == ":":
                boundaries.add(i)
            elif cur.isupper() and (prev.islower() or (nxt and nxt.islower())):
                # Treat capitals that start a word as boundaries, including QWidget (W + next lowercase).
                boundaries.add(i)
            elif prev.isdigit() and cur.isalpha():
                boundaries.add(i)
            elif prev.isalpha() and cur.isdigit():
                boundaries.add(i)

        boundary_hits = sum(1 for idx in out if idx in boundaries)
        case_hits = sum(
            1
            for pch, idx in zip(pattern, out)
            if pch.isupper() and 0 <= idx < len(candidate) and candidate[idx].isupper()
        )
        uppercase_bonus = 60.0 if any(ch.isupper() for ch in pattern) else 0.0
        start_boundary_bonus = 60.0 if out and out[0] in boundaries else 0.0
        boundary_bonus = float(boundary_hits) * 40.0
        case_bonus = float(case_hits) * 30.0

        score = base_score + boundary_bonus + case_bonus + uppercase_bonus + start_boundary_bonus

        # Strong abbreviation match: all chars hit boundaries (e.g. QW -> QWidget, cN -> createNode)
        if boundary_hits == len(p) and len(p) <= 6:
            score = max(score, 930.0 - float(out[0] * 2 + gaps * 2))

        return tuple(out), max(1.0, score)

    def _extract_identifiers(self) -> List[str]:
        text = self.editor.toPlainText()
        if text == self._cached_doc_text:
            return self._cached_identifiers

        variable_pattern = r"\b([a-zA-Z_][a-zA-Z_0-9]*)\b"
        function_pattern = r"\bdef\s+([a-zA-Z_][a-zA-Z_0-9]*)\b"
        class_pattern = r"\bclass\s+([a-zA-Z_][a-zA-Z_0-9]*)\b"

        variables = set(re.findall(variable_pattern, text))
        functions = set(re.findall(function_pattern, text))
        classes = set(re.findall(class_pattern, text))

        self._cached_doc_text = text
        self._cached_identifiers = sorted(variables | functions | classes)
        return self._cached_identifiers

    def _collect_candidates(self, context=None) -> Tuple[List[str], dict, str | None]:
        candidates: List[str] = []
        base_priority: dict = {}

        if context and context.get("type") == "node_name":
            if not CodeEditorSettings().CREATE_NODE_COMPLETER:
                return [], {}, None
            self._ensure_node_cache()
            names = sorted(self._node_cache.keys(), key=lambda n: n.lower())
            for name in names:
                base_priority.setdefault(name, 18)
            return names, base_priority, "node"

        if context and context.get("type") == "node_attr":
            if not CodeEditorSettings().CREATE_NODE_COMPLETER:
                return [], {}, None
            self._ensure_node_cache()
            try:
                obj = context.get("object")
                prefix = (context.get("prefix") or "").strip()
            except Exception:
                obj = None
                prefix = ""
            if obj is None:
                # Fall back to cached node names.
                names = sorted(self._node_cache.keys(), key=lambda n: n.lower())
                for name in names:
                    base_priority.setdefault(name, 18)
                return names, base_priority, "node"
            try:
                for name in dir(obj):
                    if not isinstance(name, str) or not name:
                        continue
                    if not prefix.startswith("_") and name.startswith("_"):
                        continue
                    # Keep only node constructors (callables).
                    try:
                        value = getattr(obj, name, None)
                    except Exception:
                        continue
                    if callable(value):
                        candidates.append(name)
                        base_priority.setdefault(name, 18)
            except Exception:
                candidates = []

            if candidates:
                return candidates, base_priority, "node"

            # Some environments may not expose node constructors via `nuke.nodes.<Name>`.
            # Fall back to the cached node list so the user still gets suggestions.
            names = sorted(self._node_cache.keys(), key=lambda n: n.lower())
            for name in names:
                base_priority.setdefault(name, 16)
            return names, base_priority, "node"

        if context and context.get("type") == "attr":
            obj = context.get("object")
            source = context.get("source") or "local"
            if obj is None:
                return [], {}, None
            try:
                names = dir(obj)
            except Exception:
                return [], {}, None

            # Hide private members unless the user started typing "_".
            try:
                prefix = (context.get("prefix") or "").strip()
            except Exception:
                prefix = ""

            for name in names:
                if not isinstance(name, str) or not name:
                    continue
                if prefix.startswith("_"):
                    candidates.append(name)
                else:
                    if name.startswith("_"):
                        continue
                    candidates.append(name)
                base_priority.setdefault(name, 15)
            # Keep attribute completion list tight.
            return candidates, base_priority, str(source)

        if nuke:
            try:
                for name in dir(nuke):
                    if name.startswith("_"):
                        continue
                    candidates.append(name)
                    base_priority[name] = 20
            except Exception:
                pass

        if self._pyside_index:
            for name in self._pyside_index.keys():
                candidates.append(name)
                base_priority.setdefault(name, 12)

        try:
            for name in dir(builtins):
                candidates.append(name)
                base_priority.setdefault(name, 10)
        except Exception:
            pass

        try:
            for name in keyword.kwlist:
                candidates.append(name)
                base_priority.setdefault(name, 5)
        except Exception:
            pass

        try:
            for name in dir(types):
                candidates.append(name)
                base_priority.setdefault(name, 1)
        except Exception:
            pass

        for name in ("@staticmethod", "@classmethod", "@property", "async def", "await"):
            candidates.append(name)
            base_priority.setdefault(name, 2)

        try:
            for name in self._extract_identifiers():
                candidates.append(name)
                base_priority.setdefault(name, 3)
        except Exception:
            pass

        # Keep unique strings while preserving priority dict.
        unique: List[str] = []
        seen = set()
        for name in candidates:
            if not isinstance(name, str) or not name:
                continue
            if name not in seen:
                seen.add(name)
                unique.append(name)
        return unique, base_priority, None

    def _ensure_node_cache(self):
        if self._node_loaded:
            return
        self._node_loaded = True
        self._node_cache = {}

        json_path = None
        try:
            json_path = os.path.join(PathFromOS().json_dynamic_path, "nodeList.json")
        except Exception:
            json_path = None

        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for row in data if isinstance(data, list) else []:
                    name = (row or {}).get("name")
                    category = (row or {}).get("category") or "Other"
                    if isinstance(name, str) and name:
                        self._node_cache[name] = category
                if self._node_cache:
                    return
            except Exception:
                pass

        if not nuke:
            return

        built = self._build_node_cache_from_nuke()
        self._node_cache.update(built)

        if json_path and self._node_cache:
            try:
                payload = [{"name": name, "category": cat} for name, cat in sorted(self._node_cache.items(), key=lambda kv: kv[0].lower())]
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
            except Exception:
                pass

    def _build_node_cache_from_nuke(self) -> dict:
        extensions = ("gizmo", "dll", "dylib", "so")
        excluded_nodes = {"A_RestoreEdgePremult"}
        excluded_prefixes = ("NST_",)

        category_map = {
            "Transform": ("transform", "move", "position", "crop"),
            "Color": ("color", "grade", "exposure", "saturation"),
            "Merge": ("merge", "combine", "blend"),
            "Filter": ("blur", "sharpen", "denoise", "filter"),
            "Channel": ("channel", "shuffle", "copy"),
            "Keyer": ("keyer", "key", "chroma"),
            "Draw": ("draw", "paint", "roto"),
            "Time": ("time", "frame", "retiming"),
        }

        def categorize(name: str) -> str:
            lowered = name.lower()
            for cat, keys in category_map.items():
                if any(k in lowered for k in keys):
                    return cat
            return "Other"

        out: dict = {}

        try:
            if hasattr(nuke, "nodes"):
                for name in dir(nuke.nodes):
                    if not isinstance(name, str) or not name or name.startswith("_"):
                        continue
                    obj = getattr(nuke.nodes, name, None)
                    if callable(obj):
                        out.setdefault(name, categorize(name))
        except Exception:
            pass

        try:
            for directory in nuke.pluginPath():
                if not directory or not os.path.exists(directory):
                    continue
                for filename in os.listdir(directory):
                    if not filename:
                        continue
                    if filename in excluded_nodes:
                        continue
                    if any(filename.startswith(pfx) for pfx in excluded_prefixes):
                        continue
                    if filename.endswith(extensions):
                        node_name = os.path.splitext(filename)[0]
                        if node_name:
                            out.setdefault(node_name, categorize(node_name))
        except Exception:
            pass

        return out
