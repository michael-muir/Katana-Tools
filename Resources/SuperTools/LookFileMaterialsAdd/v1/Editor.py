"""LookFileMaterialsAdd Editor."""

import logging

from Katana import UI4, QT4FormWidgets, QT4Widgets, Utils  # noqa

from laika_core_katana.ui_supertools import (
    create_param_widget,
)
from laika_qt.Qt import QtCore, QtGui, QtWidgets, __binding__  # noqa

LOG = logging.getLogger("laika.LookFileMaterialsAdd")


class LookFileMaterialsAddEditor(QtWidgets.QWidget):
    """Editor widget for the LookFileMaterialsAdd node."""

    def __init__(self, parent, node):
        """Initialize."""

        super().__init__(parent)

        self._node = node
        QtWidgets.QVBoxLayout(self)

        metrics = QtGui.QFontMetrics(self.font())
        width = metrics.horizontalAdvance("loaded_lookfile") + 10
        parent_policy = QT4FormWidgets.PythonGroupPolicy("parent_policy")
        parent_policy.getWidgetHints()["hideTitle"] = True
        create_param_widget(self, "assets", node, parent_policy=parent_policy, label_width=width)
        create_param_widget(
            self, "version_mode", node, parent_policy=parent_policy, label_width=width
        )
        create_param_widget(self, "add_button", node, parent_policy=parent_policy)
        create_param_widget(self, "watch_list", node, parent_policy=parent_policy)
        create_param_widget(self, "loaded_lookfiles", node, parent_policy=parent_policy)
