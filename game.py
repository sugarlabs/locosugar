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
LABELS = [_('Move the mouse to the Cuco.'),
          _('Click on the Cuco with the left button.'),
          _('Click on the Cucos with the left button.'),
          _('Click and drag the Cucos to the right.'),
          _('Type the letter on the Cuco.'),
          _('Use the SHIFT key for capital letters.'),
          _('Type the letters on the Cuco in word order.')]
ALERTS = [_('Press ENTER to confirm.'),
          _('Press DELETE to delete text.')]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MSGS = [_('Hello Cuco'), _('Cucos are not real.')]
NOISE_KEYS = ['Shift_L', 'Shift_R', 'Control_L', 'Caps_Lock', 'Pause',
              'Alt_L', 'Alt_R', 'KP_Enter', 'ISO_Level3_Shift', 'KP_Divide',
              'Escape', 'Return', 'KP_Page_Up', 'Up', 'Down', 'Menu',
              'Left', 'Right', 'KP_Home', 'KP_End', 'KP_Up', 'Super_L',
              'KP_Down', 'KP_Left', 'KP_Right', 'KP_Page_Down', 'Scroll_Lock',
              'Page_Down', 'Page_Up']
WHITE_SPACE = ['space', 'Tab']
PUNCTUATION = {'period': '.', 'comma': ',', 'question': '?', 'exclam': '!'}
DEAD_KEYS = ['grave', 'acute', 'circumflex', 'tilde', 'diaeresis', 'abovering']
DEAD_DICTS = [{'A': 192, 'E': 200, 'I': 204, 'O': 210, 'U': 217, 'a': 224,
               'e': 232, 'i': 236, 'o': 242, 'u': 249},
              {'A': u'Á', 'E': u'É', 'I': u'Í', 'O': u'Ó', 'U': u'Ú',
               'a': u'á', 'e': u'é', 'i': u'í', 'o': u'ó', 'u': u'ú'},
              {'A': 194, 'E': 202, 'I': 206, 'O': 212, 'U': 219, 'a': 226,
               'e': 234, 'i': 238, 'o': 244, 'u': 251},
              {'A': 195, 'O': 211, 'N': u'Ñ', 'U': 360, 'a': 227, 'o': 245,
               'n': u'ñ', 'u': 361},
              {'A': 196, 'E': 203, 'I': 207, 'O': 211, 'U': 218, 'a': 228,
               'e': 235, 'i': 239, 'o': 245, 'u': 252},
              {'A': 197, 'a': 229}]


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
        self._pause = 200
        self._press = None
        self._clicked = False
        self._dead_key = ''
        self._waiting_for_delete = False
        self._waiting_for_enter = False
        self._seconds = 0
        self._timer_id = None
        self.level = 0
        self.score = 0

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)

        self._BG = ['background0.jpg', 'background0.jpg', 'background0.jpg',
                    'background1.jpg', 'background2.jpg', 'background2.jpg',
                    'background2.jpg']
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
        self._panel.set_label_attributes(20)
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
        for i in range(len(MSGS[1])):  # Check re i18n
            self._sticky_cards.append(Sprite(self._sprites, 0, 0,
                                             self._cuco_pixbuf))
            self._sticky_cards[-1].type = 'cuco'
            self._sticky_cards[-1].set_label_attributes(24,
                                                        vert_align='bottom')

        self._all_clear()

    def _time_increment(self):
        ''' Track seconds since start_time. '''
        self._seconds = int(gobject.get_current_time() - self._start_time)
        self.timer_id = gobject.timeout_add(1000, self._time_increment)

    def _timer_reset(self):
        ''' Reset the timer for each level '''
        self._start_time = gobject.get_current_time()
        if self._timer_id is not None:
            gobject.source_remove(self._timer_id)
            self._timer_id = None
        self.score += self._seconds
        self._time_increment()

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
            p.set_label_color('white')
            p.hide()
        self._backgrounds[self.level].set_layer(BG_LAYER)

    def new_game(self, first_time):
        ''' Start a new game at the current level. '''
        self._first_time = first_time
        self._clicked = False

        # It may be time to advance to the next level.
        if (self.level == 6 and self._counter == len(MSGS)) or \
           self._counter > 5:
            self._first_time = True
            self.level += 1
            self._counter = 0
            self._correct = 0
            self._pause = 200
            self._parent.timer_label.set_text(
                '%d:%02d' % (int(self.score / 60.), self.score % 60))
            if self.level == len(self._backgrounds):
                self.level = 0
                self.score = 0
                self._parent.unfullscreen()

        self._all_clear()

        if self._first_time:
            # Every game starts by putting up a panel with instructions
            # The panel disappears on mouse movement
            self._panel.set_label(LABELS[self.level])
            self._panel.set_layer(PANEL_LAYER)
            self._timer_reset()

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
                self._cuco_quadrant = int(uniform(2, 4))
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
        elif self.level == 4:
            # Place some Cucos on the canvas with letters as labels
            # Just lowercase
            for i in range(self._counter + 1):
                self._cuco_quadrant = int(uniform(0, 4))
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
                self._sticky_cards[i].set_label(
                    ALPHABET[int(uniform(26, len(ALPHABET)))])
        elif self.level == 5:
            # Place some Cucos on the canvas with letters as labels
            # Mixed case
            for i in range(self._counter + 1):
                self._cuco_quadrant = int(uniform(0, 4))
                x, y = self._quad_to_xy(self._cuco_quadrant)
                self._sticky_cards[i].move((x, y))
                self._sticky_cards[i].type = 'cuco'
                self._sticky_cards[i].set_layer(CUCO_LAYER)
                self._sticky_cards[i].set_label(
                    ALPHABET[int(uniform(0, len(ALPHABET)))])
        elif self.level == 6:
            x = 0
            y = 0
            c = 0
            for i in range(len(MSGS[self._counter])):
                if MSGS[self._counter][i] == ' ':
                    y += self._cuco_dim[1]
                    x = 0
                else:
                    self._sticky_cards[c].move((x, y))
                    self._sticky_cards[c].type = i
                    self._sticky_cards[c].set_layer(CUCO_LAYER)
                    self._sticky_cards[c].set_label(MSGS[self._counter][i])
                    c += 1
                    x += int(self._cuco_dim[0] / 2.)

        if self.level in [0, 1]:
            self._cuco_quadrant += int(uniform(1, 4))
            self._cuco_quadrant %= 4
            x, y = self._quad_to_xy(self._cuco_quadrant)
            if self.level == 0:
                self._move_cuco(x, y, 0)
            else:
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
            gobject.idle_add(play_audio_from_file, self, os.path.join(
                    self._path, 'sounds', 'taunt.ogg'))

        self._taunt_cards[(i + 1) % 2].hide()
        if self._clicked:
            self._timeout_id = None
            return True
        else:
            self._taunt_cards[i % 2].move((x, y))
            self._taunt_cards[i % 2].set_layer(CUCO_LAYER)
            self._timeout_id = gobject.timeout_add(
                200, self._taunt, x, y, i + 1)

    def _move_cuco(self, x, y, i):
        if i == 0:
            gobject.idle_add(play_audio_from_file, self, os.path.join(
                    self._path, 'sounds', 'move.ogg'))
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
            if self._pause > 50:
                self._pause -= 10
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
                self._pause, self._move_cuco, x, y, j)

    def _keypress_cb(self, area, event):
        ''' Keypress '''
        # Games 4, 5, and 6 use the keyboard
        if self.level not in [4, 5, 6]:
            return True
        k = gtk.gdk.keyval_name(event.keyval)
        u = gtk.gdk.keyval_to_unicode(event.keyval)

        if self._waiting_for_enter:
            if k == 'Return':
                self._waiting_for_enter = False
                self._panel.hide()
                self._counter += 1
                self._correct = 0
                gobject.timeout_add(1000, self.new_game, False)
            return

        if k in NOISE_KEYS or k in WHITE_SPACE:
            return True

        if self.level == 6 and self._waiting_for_delete:
            if k in ['BackSpace', 'Delete']:
                self._waiting_for_delete = False
                self._sticky_cards[self._correct].set_label_color('white')
                self._sticky_cards[self._correct].set_label(
                    MSGS[self._counter][
                        self._sticky_cards[self._correct].type])
                self._panel.hide()
                self._panel.set_label_color('black')
            return

        if k[0:5] == 'dead_':
            self._dead_key == keyname
            return
        if self._dead_key is not '':
            k = DEAD_DICTS[DEAD_KEYS.index(self.dead_key[5:])][k]
            self._dead_key = ''

        if self.level == 6:
            n = len(MSGS[self._counter])
        else:
            n = self._counter + 1

        if self.level == 6:
            i = self._correct
            if k in PUNCTUATION:
                k = PUNCTUATION[k]
            elif len(k) > 1:
                return True
            if self._sticky_cards[i].labels[0] == k:
                self._sticky_cards[i].set_label_color('blue')
                self._sticky_cards[i].set_label(k)
                self._correct += 1
            else:
                self._sticky_cards[i].set_label_color('red')
                self._sticky_cards[i].set_label(k)
                self._panel.set_label_color('red')
                self._panel.set_label(ALERTS[1])
                self._panel.set_layer(PANEL_LAYER)
                self._waiting_for_delete = True
                gobject.idle_add(play_audio_from_file, self, os.path.join(
                        self._path, 'sounds', 'error.ogg'))
        else:
            for i in range(n):
                if self._sticky_cards[i].labels[0] == k:
                    self._sticky_cards[i].set_label('')
                    break

        # Test for end condition
        if self.level == 6 and \
           self._correct == len(MSGS[self._counter]) - \
                            MSGS[self._counter].count(' '):
            c = 0
            for i in range(len(MSGS[self._counter])):
                if MSGS[self._counter][i] == ' ':
                    continue
                elif MSGS[self._counter][i] != self._sticky_cards[c].labels[0]:
                    return True
                c += 1
            self._panel.set_label(ALERTS[0])
            self._panel.set_layer(PANEL_LAYER)
            self._waiting_for_enter = True
            return
        else:
            for i in range(n):
                if len(self._sticky_cards[i].labels[0]) > 0:
                    return True
        self._counter += 1
        self._correct = 0
        gobject.timeout_add(1000, self.new_game, False)

    def _mouse_move_cb(self, win, event):
        ''' Move the mouse. '''
        # Games 0, 3, 4, and 5 use move events
        win.grab_focus()
        x, y = map(int, event.get_coords())
        if self._seconds > 1:
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
        elif self.level in [4, 5]:
            # For Game 4 and 5, we allow dragging
            if self._press is None:
                self._drag_pos = [0, 0]
                return True
            dx = x - self._drag_pos[0]
            dy = y - self._drag_pos[1]
            self._press.move_relative((dx, dy))
            self._drag_pos = [x, y]
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
        # Game 3 uses release
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
        if spr is None:
            return
        if spr.type != 'cuco':
            return
        if self.level < 2 and self._timeout_id is None:
            return
        if self._clicked:
            return

        # Games 1, 2, and 3 involve clicks; Games 4 and 5 allow click to drag
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
            if self._correct == self._counter:
                self._counter += 1
                self._correct = 0
                gobject.timeout_add(2000, self.new_game, False)
            else:
                self._correct += 1
        elif self.level in [3, 4, 5]:
            # In Games 4 and 5, dragging is used to remove overlaps
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
