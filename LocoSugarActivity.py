#Copyright (c) 2012 Walter Bender
#Copyright (c) 2012 Ignacio Rodriguez

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

from gi.repository import Gtk, GObject, Gdk

from sugar3.activity import activity
from sugar3 import profile
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.datastore import datastore
from sugar3 import mime

from gettext import gettext as _

from game import Game
from toolbar_utils import separator_factory

import logging
_logger = logging.getLogger('loco-activity')


class LocoSugarActivity(activity.Activity):
    ''' Simplified Loco activity rewritten in Python '''

    def __init__(self, handle):
        ''' Initialize the toolbars and the game board '''
        super(LocoSugarActivity, self).__init__(handle)

        self.path = activity.get_bundle_path()

        self._setup_toolbars()

        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(), \
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, path=self.path)
        if 'level' in self.metadata:
            self._game.level = int(self.metadata['level'])
        if 'score' in self.metadata:
            self._game.score = int(self.metadata['score'])
        self.fullscreen()
        GObject.timeout_add(1000, self._game.new_game, True)

    def _setup_toolbars(self):
        ''' Setup the toolbars. '''

        self.max_participants = 1  # No collaboration

        toolbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)

        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.set_toolbar_box(toolbox)
        toolbox.show()
        self.toolbar = toolbox.toolbar

        separator_factory(toolbox.toolbar, True, False)

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

    def write_file(self, file_path):
        ''' Save the play level '''
        if hasattr(self, '_game'):
            self.metadata['level'] = str(self._game.level)
            self.metadata['score'] = str(self._game.score)
