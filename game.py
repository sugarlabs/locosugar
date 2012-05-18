# -*- coding: utf-8 -*-
#Copyright (c) 2012 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


import gtk
import gobject
import cairo
import os
import glob
from random import uniform

from gettext import gettext as _

import logging
_logger = logging.getLogger('cuco-activity')

try:
    from sugar.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0

from sprites import Sprites, Sprite
from play_audio import play_audio_from_file

CUCO_LAYER = 2
PANEL_LAYER = 1
BG_LAYER = 0
LABELS = [_('Move the mouse to the Cuco'),
          _('Click on the Cuco with the left button.'),
          _('Click on the Cucos with the left button.'),
          _('Click and drag the Cucos to the right.'),
          _('Type the letter on the Cuco'),
          _('Write the word formed by the Cucos. For exclamation points and capital letters have to use the SHIFT key')]
ALERTS = [_('Press ENTER to confirm'),
          _('Press DELETE to delete all text '),
          _('Prees the CLEAR key to clear what is wrong')]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
#    u'ÑñáéíóúÁÉÍÓÚ'

class Game():

    def __init__(self, canvas, parent=None, path=None):
        self._canvas = canvas
        self._parent = parent
        self._parent.show_all()
        self._path = path

        self._canvas.set_flags(gtk.CAN_FOCUS)
        self._canvas.connect("expose-event", self._expose_cb)
        self._canvas.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self._canvas.connect("button-press-event", self._button_press_cb)
        self._canvas.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self._canvas.connect("motion-notify-event", self._mouse_move_cb)
        self._canvas.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
        self._canvas.connect('button-release-event', self._button_release_cb)
        self._canvas.connect('key_press_event', self._keypress_cb)

        self._width = gtk.gdk.screen_width()
        self._height = gtk.gdk.screen_height()
        self._scale = self._width / 1200.
        self._first_time = True
        self._cuco_pos = (0, 0)
        self._cuco_dim = (0, 0)
        self._cuco_quadrant = 3
        self._drag_pos = [0, 0]
        self._counter = 0
        self._correct = 0
        self._timeout_id = None
        self._press = None
        self._clicked = False

        self.level = 0
        self.pause = 200

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)

        self._BG = ['background0.jpg', 'background1.jpg', 'background2.jpg',
                    'background3.jpg', 'background4.jpg']
        self._backgrounds = []
        for bg in self._BG:
            self._backgrounds.append(Sprite(
                    self._sprites, 0, 0, gtk.gdk.pixbuf_new_from_file_at_size(
                        os.path.join(self._path, 'images', bg),
                        self._width, self._height)))
            self._backgrounds[-1].type = 'background'
            self._backgrounds[-1].hide()

        self._panel = Sprite(
            self._sprites, int(400 * self._scale), int(400 * self._scale),
            gtk.gdk.pixbuf_new_from_file_at_size(
                os.path.join(self._path, 'images', 'ventana.png'),
                int(720 * self._scale), int(370 * self._scale)))
        self._panel.type = 'panel'
        self._panel.set_label(LABELS[0])
        self._panel.hide()
        
        self._CUCOS = glob.glob(
                os.path.join(self._path, 'images', 'cuco*.png'))
        self._cuco_cards = []
        for cuco in self._CUCOS:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                cuco, int(258 * self._scale), int(208 * self._scale))
            self._cuco_cards.append(Sprite(self._sprites, 0, 0, pixbuf))
            self._cuco_cards[-1].type = 'cuco'
        self._cuco_dim = (int(258 * self._scale), int(208 * self._scale))

        self._MEN = glob.glob(
                os.path.join(self._path, 'images', 'man*.png'))
        self._man_cards = []
        for cuco in self._MEN:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                cuco, int(258 * self._scale), int(208 * self._scale))
            self._man_cards.append(Sprite(self._sprites, 0, 0, pixbuf))
            self._man_cards[-1].type = 'cuco'

        self._TAUNTS = glob.glob(
                os.path.join(self._path, 'images', 'taunt*.png'))
        self._taunt_cards = []
        for cuco in self._TAUNTS:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                cuco, int(258 * self._scale), int(208 * self._scale))
            self._taunt_cards.append(Sprite(self._sprites, 0, 0, pixbuf))
            self._taunt_cards[-1].type = 'cuco'

        self._GHOSTS = glob.glob(
                os.path.join(self._path, 'images', 'ghost*.png'))
        self._ghost_cards = []
        for cuco in self._GHOSTS:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                cuco, int(258 * self._scale), int(208 * self._scale))
            self._ghost_cards.append(Sprite(self._sprites, 0, 0, pixbuf))
            self._ghost_cards[-1].type = 'cuco'

        self._sticky_cards = []
        self._cuco_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
            self._CUCOS[0], int(258 * self._scale), int(208 * self._scale))
        self._man_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
            self._MEN[0], int(258 * self._scale), int(208 * self._scale))
        self._ghost_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
            self._GHOSTS[0], int(258 * self._scale), int(208 * self._scale))
        for i in range(10):
            self._sticky_cards.append(Sprite(self._sprites, 0, 0,
                                             self._cuco_pixbuf))
            self._sticky_cards[-1].type = 'cuco'
            self._sticky_cards[-1].set_label_color('white')
            self._sticky_cards[-1].set_label_attributes(24,
                                                        vert_align='bottom')

        self._all_clear()

    def _all_clear(self):
        ''' Things to reinitialize when starting up a new game. '''
        for p in self._cuco_cards:
            p.hide()
        for p in self._man_cards:
            p.hide()
        for p in self._taunt_cards:
            p.hide()
        for p in self._ghost_cards:
            p.hide()
        for p in self._sticky_cards:
            p.set_shape(self._cuco_pixbuf)
            p.set_label('')
            p.hide()
        self._backgrounds[self.level].set_layer(BG_LAYER)

    def new_game(self, first_time):
        ''' Start a new game. '''
        self._first_time = first_time
        self._clicked = False

        if self._counter > 1: # 9
            self._first_time = True
            self.level += 1
            _logger.debug('beginning level %d' % (self.level))
            self._counter = 0
            self._correct = 0
            self._pause = 200
            if self.level == len(self._backgrounds):
                self.level = 0
                self._parent.unfullscreen()

        self._all_clear()

        if self._first_time:
            # Every game starts by putting up a panel with instructions
            # The panel disappears on mouse movement
            self._panel.set_label(LABELS[self.level])
            self._panel.set_layer(PANEL_LAYER)

        if self.level == 0:
            # Choose a random location for the Cuco
            self._cuco_quadrant += int(uniform(1, 4))
            self._cuco_quadrant %= 4
            x, y = self._quad_to_xy(self._cuco_quadrant)
            self._cuco_cards[0].move((x, y))
            self._cuco_pos = (x, y)
        elif self.level == 2:
            # Place some Cucos on the canvas
            for i in range(self._counter + 1):
                self._cuco_quadrant += int(uniform(1, 4))
                self._cuco_quadrant %= 4
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
        elif self.level == 3:
            # Place some Cucos on the left-side of the canvas
            for i in range(self._counter + 1):
                self._cuco_quadrant += int(uniform(2, 4))
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
        elif self.level == 4:
            # Place some Cucos on the canvas with letters as labels
            for i in range(self._counter + 1):
                self._cuco_quadrant += int(uniform(0, 4))
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
                self._sticky_cards[i].set_label(
                    ALPHABET[int(uniform(0, len(ALPHABET)))])

        if self.level in [0, 1]:
            self._cuco_quadrant += int(uniform(1, 4))
            self._cuco_quadrant %= 4
            x, y = self._quad_to_xy(self._cuco_quadrant)
            if self.level == 0:
                self._move_cuco(x, y, 0)
            elif self.level == 1:
                self._taunt(x, y, 0)

    def _quad_to_xy(self, q):
        x = int(max(0, (self._width / 2.) * uniform(0, 1) - self._cuco_dim[0]))
        if q in [0, 1]:
            x += int(self._width / 2.)
        y = int(max(0, (self._height / 2.) * uniform(0, 1) - self._cuco_dim[1]))
        if q in [1, 2]:
            y += int(self._height / 2.)
        return x, y

    def _taunt(self, x, y, i):
        if i == 0:
            play_audio_from_file(self, os.path.join(
                    self._path, 'sounds', 'taunt.ogg'))

        self._taunt_cards[(i + 1)%2].hide()
        if self._clicked:
            self._timeout_id = None
            return True
        else:
            self._taunt_cards[i%2].move((x, y))
            self._taunt_cards[i%2].set_layer(CUCO_LAYER)
            self._timeout_id = gobject.timeout_add(
                200, self._taunt, x, y, i + 1)

    def _move_cuco(self, x, y, i):
        j = (i + 1) % len(self._cuco_cards)
        cx, cy = self._cuco_cards[i].get_xy()
        dx = cx - x
        dy = cy - y
        if dx * dx + dy * dy < 100:
            self._cuco_cards[j].move((x, y))
            self._cuco_pos = (x, y)
            self._cuco_cards[j].hide()
            self._cuco_cards[i].hide()
            self._man_cards[0].move((x, y))
            self._man_cards[0].set_layer(CUCO_LAYER)
            self._timeout_id = None
            if self.pause > 50:
                self.pause -= 10
            return True
        else:
            if dx > 0:
                cx -= 5
            elif dx < 0:
                cx += 5
            if dy > 0:
                cy -= 5
            elif dy < 0:
                cy += 5
            self._cuco_cards[j].move((cx, cy))
            self._cuco_pos = (cx, cy)
            self._cuco_cards[j].set_layer(CUCO_LAYER)
            self._cuco_cards[i].hide()
            self._timeout_id = gobject.timeout_add(
                self.pause, self._move_cuco, x, y, j)

    def _keypress_cb(self, area, event):
        ''' Keypress '''
        k = gtk.gdk.keyval_name(event.keyval)
        u = gtk.gdk.keyval_to_unicode(event.keyval)
        for i in range(self._counter + 1):
            if self._sticky_cards[i].labels[0] == k:
                self._sticky_cards[i].set_label('')
        for i in range(self._counter + 1):
            if len(self._sticky_cards[i].labels[0]) > 0:
                return True
        self._counter += 1
        gobject.timeout_add(1000, self.new_game, False)

    def _mouse_move_cb(self, win, event):
        ''' Move the mouse. '''
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self._panel.hide()
        if not self._clicked and self.level == 0:
            # For Game 0, see if the mouse is on the Cuco
            dx = x - self._cuco_pos[0] - self._cuco_dim[0] / 2.
            dy = y - self._cuco_pos[1] - self._cuco_dim[1] / 2.
            if dx * dx + dy * dy < 200:
                self._clicked = True
                if self._timeout_id is not None:
                    gobject.source_remove(self._timeout_id)
                # Play again
                self._all_clear()
                self._man_cards[0].move((x - int(self._cuco_dim[0] / 2.),
                                         y - int(self._cuco_dim[1] / 2.)))
                self._man_cards[0].set_layer(CUCO_LAYER)
                self._correct += 1
                self._counter += 1
                gobject.timeout_add(1000, self.new_game, False)
        elif self.level == 3:
            # For Game 3, we are dragging
            if self._press is None:
                self._drag_pos = [0, 0]
                return True
            dx = x - self._drag_pos[0]
            dy = y - self._drag_pos[1]
            self._press.move_relative((dx, dy))
            self._drag_pos = [x, y]
            if x > self._width / 2.:
                self._press.set_shape(self._man_pixbuf)
                if self._press.type == 'cuco':
                    self._correct += 1
                    self._press.type = 'man'
        return True

    def _button_release_cb(self, win, event):
        if self.level == 3:
            # Move to release
            if self._correct == self._counter + 1:
                self._counter += 1
                self._correct = 0
                gobject.timeout_add(2000, self.new_game, False)
        self._press = None
        self._drag_pos = [0, 0]
        return True

    def _button_press_cb(self, win, event):
        self._press = None
        win.grab_focus()
        x, y = map(int, event.get_coords())
        if self.level == 0:
            return
        spr = self._sprites.find_sprite((x, y))
        if spr == None:
            self._correct = 0
            return
        if spr.type != 'cuco':
            self._correct = 0
            return
        if self._timeout_id is None:
            return
        if self._clicked:
            return

        # For Game 1, click on the Cuco
        if self.level == 1:
            self._all_clear()
            self._man_cards[0].move((x - int(self._cuco_dim[0] / 2.),
                                     y - int(self._cuco_dim[1] / 2.)))
            self._man_cards[0].set_layer(CUCO_LAYER)
            self._clicked = True
            self._counter += 1
            self._correct += 1
            if self._timeout_id is not None:
                gobject.source_remove(self._timeout_id)
            gobject.timeout_add(2000, self.new_game, False)
        elif self.level == 2:
            spr.set_shape(self._ghost_pixbuf)
            spr.type = 'ghost'
            self._correct += 1
            if self._correct == self._counter + 1:
                self._counter += 1
                self._correct = 0
                gobject.timeout_add(2000, self.new_game, False)
        elif self.level == 3:
            self._press = spr
            self._drag_pos = [x, y]
        return True

    def _expose_cb(self, win, event):
        self.do_expose_event(event)

    def do_expose_event(self, event):
        ''' Handle the expose-event by drawing '''
        # Restrict Cairo to the exposed area
        cr = self._canvas.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                event.area.width, event.area.height)
        cr.clip()
        # Refresh sprite list
        self._sprites.redraw_sprites(cr=cr)

    def _destroy_cb(self, win, event):
        gtk.main_quit()
