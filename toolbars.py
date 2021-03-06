# toolbars.py
#
# Classes defining toolbars for Classroom Presenter
# B. Mayton <bmayton@cs.washington.edu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from sugar3.activity import activity
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.datastore import datastore

import logging
import threading
import os
import sys
from time import strftime
import utils
from path import path
import slideshow
import subprocess
import listview

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Pango
from gi.repository import GObject
#from gi.repository import WebKit
#from gi.repository.WebKit import WebView

from sugar3 import env

#from hulahop.webview import WebView

DATASTORE = '/home/olpc/.sugar/default/datastore/store'


def get_mounts():
    volume_monitor = Gio.VolumeMonitor.get()

    mounts = []
    for volume in volume_monitor.get_volumes(
    ):  # Get all volumes (mounted and no mounted)

        print "GETTING VOLUMES", volume.get_name(), volume.get_identifier("uuid")

        if not volume.get_mount():  # Is not mounted
            continue

        mount = volume.get_mount()
        description = {}
        description['uri'] = mount.get_default_location().get_path()
        description['title'] = mount.get_name()
        description['id'] = volume.get_identifier("uuid")
        mounts.append(description)

    return mounts


class NavToolBar(Gtk.Toolbar):

    def __init__(self, activity, shared, deck):
        Gtk.Toolbar.__init__(self)

        self.__deck = deck
        self.__activity = activity
        self.__shared = shared
        self.__logger = logging.getLogger('Navigation Toolbar')

        self.__is_initiating = True

        self.__prevbtn = ToolButton('go-previous')
        self.__prevbtn.set_tooltip("Previous slide")
        self.__prevbtn.connect('clicked', self.previous)
        self.insert(self.__prevbtn, -1)
        self.__prevbtn.show()

        self.__nextbtn = ToolButton('go-next')
        self.__nextbtn.set_tooltip("Next slide")
        self.__nextbtn.connect('clicked', self.next)
        self.insert(self.__nextbtn, -1)
        self.__nextbtn.show()

        # page number widget and navigation
        self.__num_page_item = Gtk.ToolItem()
        self.__num_current_page = 1

        self.__num_page_entry = Gtk.Entry()
        self.__num_page_entry.set_text(str(self.__num_current_page))
        self.__num_page_entry.set_alignment(1)
        self.__num_page_entry.connect('activate', self.num_page_activate)

        self.__num_page_entry.set_width_chars(4)

        self.__num_page_item.add(self.__num_page_entry)
        self.__num_page_entry.show()

        self.insert(self.__num_page_item, -1)
        self.__num_page_item.show()

        # total page number widget
        self.__total_page_item = Gtk.ToolItem()
        self.__total_page_label = Gtk.Label(
            ' / ' + str(self.__deck.getSlideCount()))
        self.__total_page_label.modify_font(Pango.FontDescription("14"))
        self.__total_page_label.modify_fg(
            Gtk.StateType.NORMAL, Gdk.Color(
                65535, 65535, 65535))
        self.__total_page_item.add(self.__total_page_label)
        self.__total_page_label.show()

        self.insert(self.__total_page_item, -1)
        self.__total_page_item.show()

        # separator between navigation buttons and lock button
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        # unlocked button
        self.__unlockBtn = ToolButton('unlocked')
        self.__unlockBtn.set_tooltip("Student Navigation Unlocked")

        # navigation is unlocked by default, so insert the unlock button
        self.insert(self.__unlockBtn, 5)
        self.__unlockBtn.show()

        # locked button
        self.__lockBtn = ToolButton('locked')
        self.__lockBtn.set_tooltip("Student Navigation Locked")

        self.__logger.debug(
            "Connecting to navigation locking and activity sharing signals.")
        self.__activity.connect('shared', self.activity_shared_cb)
        self.__activity.connect('joined', self.activity_joined_cb)
        self.__shared.connect('navigation-lock-change', self.set_lock_button)

        # triggers for when slides are changed
        self.__deck.connect("slide-changed", self.slide_changed)
        self.__deck.connect("deck-changed", self.slide_changed)
        self.slide_changed(self.__deck)
        self.show()

    def activity_shared_cb(self, widget):
        # Callback for when the activity is shared
        # bind the lock button click with switching lock mode
        self.__lockBtn.connect('clicked', self.__shared.lock_mode_switch)
        self.__unlockBtn.connect('clicked', self.__shared.lock_mode_switch)

    def activity_joined_cb(self, widget):
        """ Callback for when the activity is joined """
        self.__is_initiating = False

    def set_lock_button(self, widget, is_locked):
        self.__logger.debug("Changing lock button, lock mode %u, init %u",
                            is_locked, self.__is_initiating)
        if is_locked:
            new_button = self.__lockBtn
            if not self.__is_initiating:
                self.__prevbtn.set_sensitive(False)
                self.__nextbtn.set_sensitive(False)
        else:
            new_button = self.__unlockBtn
            if not self.__is_initiating:
                self.__prevbtn.set_sensitive(True)
                self.__nextbtn.set_sensitive(True)

        old = self.get_nth_item(5)
        self.remove(old)
        self.insert(new_button, 5)
        new_button.show()
        self.queue_draw()

    def next(self, widget):
        self.__deck.next()

    def previous(self, widget):
        self.__deck.previous()

    def slide_changed(self, widget):
        self.__logger.debug("Changing slides!")
        if self.__deck.isAtBeginning():
            self.__prevbtn.set_sensitive(False)
        else:
            self.__prevbtn.set_sensitive(True)
        if self.__deck.isAtEnd():
            self.__nextbtn.set_sensitive(False)
        else:
            self.__nextbtn.set_sensitive(True)

        self.__num_current_page = self.__deck.getIndex()
        self.__num_page_entry.set_text(str(self.__num_current_page + 1))
        self.__total_page_label.set_text(
            ' / ' + str(self.__deck.getSlideCount()))

    def num_page_activate(self, entry):
        page_entered = int(entry.get_text())

        if page_entered < 1:
            page_entered = 1
        elif self.__deck.getSlideCount() < page_entered:
            page_entered = self.__deck.getSlideCount()

        self.__deck.goToIndex(page_entered - 1, is_local=True)


class InkToolBar(Gtk.Toolbar):

    # Constructor
    def __init__(self, slideviewer, deck):

        Gtk.Toolbar.__init__(self)

        self.__slideviewer = slideviewer
        self.__cur_color = slideviewer.get_color()
        self.__cur_color_str = "blue"
        self.__cur_pen = slideviewer.get_pen()
        self.__deck = deck
        self.__deck.connect('slide-redraw', self.update_buttons)
        self.__slideviewer.connect('undo-redo-changed', self.update_buttons)
        self.__is_instr = False

        # Red Ink
        self.__red = Gtk.RadioToolButton()
        self.__red.set_icon_name('red-button')
        self.insert(self.__red, -1)
        self.__red.show()
        #self.__red.set_tooltip('Red Ink')
        self.__red.connect('clicked', self.set_ink_color, 1.0, 0.0, 0.0, "red")

        # Green Ink
        self.__green = Gtk.RadioToolButton(group=self.__red)
        self.__green.set_icon_name('green-button')
        self.insert(self.__green, -1)
        self.__green.show()
        #self.__green.set_tooltip('Green Ink')
        self.__green.connect(
            'clicked',
            self.set_ink_color,
            0.0,
            1.0,
            0.0,
            "green")

        # Blue Ink
        self.__blue = Gtk.RadioToolButton(group=self.__red)
        self.__blue.set_icon_name('blue-button')
        self.insert(self.__blue, -1)
        self.__blue.show()
        #self.__blue.set_tooltip('Blue Ink')
        self.__blue.connect(
            'clicked',
            self.set_ink_color,
            0.0,
            0.0,
            1.0,
            "blue")

        # Black Ink
        self.__black = Gtk.RadioToolButton(group=self.__red)
        self.__black.set_icon_name('black-button')
        self.insert(self.__black, -1)
        self.__black.show()
        #self.__black.set_tooltip('Black Ink')
        self.__black.connect(
            'clicked',
            self.set_ink_color,
            0.0,
            0.0,
            0.0,
            "black")

        # Separate ink from untensils
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        self.insert(separator, -1)
        separator.show()

        # Pencil
        self.__pencil = Gtk.RadioToolButton()
        self.__pencil.set_icon_name('tool-pencil')
        self.insert(self.__pencil, -1)
        self.__pencil.show()
        # self.__pencil.set_tooltip('Pencil')
        self.__pencil.connect('clicked', self.set_cur_pen, 4)

        # Brush
        self.__brush = Gtk.RadioToolButton(self.__pencil)
        self.__brush.set_icon_name('tool-brush')
        self.insert(self.__brush, -1)
        self.__brush.show()
        # self.__brush.set_tooltip('Brush')
        self.__brush.connect('clicked', self.set_cur_pen, 8)

        # Erase
        self.__erase = ToolButton('tool-eraser')
        self.insert(self.__erase, -1)
        self.__erase.show()
        self.__erase.set_tooltip('Erase All Ink')
        self.__erase.connect('clicked', self.set_erase)

        """
        # Text
        self.__text = ToolButton('text')
        self.insert(self.__text, -1)
        self.__text.show()
        self.__text.set_tooltip('Text')
        """

        # Separate tools from text
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        self.insert(separator, -1)
        separator.show()

        # Undo
        self.__undo = ToolButton('edit-undo')
        self.insert(self.__undo, -1)
        self.__undo.show()
        self.__undo.set_tooltip('Undo')
        self.__undo.connect('clicked', self.undo)

        # Redo
        self.__redo = ToolButton('edit-redo')
        self.insert(self.__redo, -1)
        self.__redo.show()
        self.__redo.set_tooltip('Redo')
        self.__redo.connect('clicked', self.redo)

        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        # FIXME (though actually not a terrible icon)
        self.__submit = ToolButton('dialog-ok')
        self.insert(self.__submit, -1)
        self.__submit.show()
        self.__submit.set_tooltip('Broadcast Submission')
        self.__submit.connect('clicked', self.submit_ink)

        self.__deck.connect('instr_state_propagate', self.instructor_state_cb)

        self.set_tool_buttons()
        self.show()

    def instructor_state_cb(self, widget, is_instr):
        self.__is_instr = is_instr
        if is_instr:
            self.__submit.set_tooltip('Broadcast Submission')
        else:
            self.__submit.set_tooltip('Submit Ink')

    def set_cur_pen(self, widget, size):
        self.__slideviewer.set_pen(size)

    def set_ink_color(self, widget, r, g, b, color):
        self.__slideviewer.set_color(r, g, b)

    def set_erase(self, widget):
        self.__slideviewer.clear_ink()

    def set_tool_buttons(self):
        if self.__cur_color == (1.0, 0.0, 0.0):
            self.__red.set_active(True)
        elif self.__cur_color == (0.0, 1.0, 0.0):
            self.__green.set_active(True)
        elif self.__cur_color == (0.0, 0.0, 1.0):
            self.__blue.set_active(True)
        else:
            self.__black.set_active(True)

        if self.__cur_pen == 2:
            self.__pencil.set_active(True)
        elif self.__cur_pen == 5:
            self.__brush.set_active(True)

    def submit_ink(self, widget):
        if self.__is_instr:
            self.broadcast_ink()
        else:
            self.__submit.set_sensitive(False)
            self.__timer = threading.Timer(3.0, self.reenable_submissions)
            self.__timer.start()
            self.__slideviewer.submit_ink()

    def broadcast_ink(self):
        self.__slideviewer.broadcast_ink()

    def reenable_submissions(self):
        self.__submit.set_sensitive(True)
        self.__submit.queue_draw()

    def undo(self, widget):
        self.__slideviewer.undo()

    def redo(self, widget):
        self.__slideviewer.redo()

    def update_buttons(self, widget=None):
        can_undo, can_redo = self.__slideviewer.can_undo_redo()
        self.__undo.set_sensitive(can_undo)
        self.__redo.set_sensitive(can_redo)
        if self.__is_instr:
            if self.__deck.getActiveSubmission() == -1:
                self.__submit.set_sensitive(False)
            else:
                self.__submit.set_sensitive(True)


class MakeToolBar(Gtk.Toolbar):

    def __init__(self, this_activity, deck):
        Gtk.Toolbar.__init__(self)
        self.activity = this_activity
        self.deck = deck

        # get mount points
        ds_mounts = get_mounts()
        pendrive = -1
        for i in range(0, len(ds_mounts), 1):
            print 'mount', i, ds_mounts[i]['uri'], ds_mounts[i]['title'], ds_mounts[i]['id']
            if ds_mounts[i]['uri'].find('datastore') > 0:
                journal = i
            else:
                pendrive = i

        #self.__newbtn = ToolButton('new-transparency')
        #self.__newbtn.set_tooltip("New slideshow")
        #self.__newbtn.connect('clicked', self.new)
        #self.insert(self.__newbtn, -1)
        # self.__newbtn.show()

        self.__openbtn = ToolButton('showntell-activity')
        self.__openbtn.set_tooltip("Choose slideshow")
        self.__openbtn.connect('clicked', self.open)
        self.insert(self.__openbtn, -1)
        self.__openbtn.show()

        #self.__htmlbutton = ToolButton('new')
        #self.__htmlbutton.set_tooltip("test tw")
        #self.__htmlbutton.connect('clicked', self.showhtml)
        #self.insert(self.__htmlbutton, -1)
        # self.__htmlbutton.show()

        self.__journalbtn = ToolButton('activity-journal')
        self.__journalbtn.set_tooltip("Choose image")
        #self.__journalbtn.connect('clicked', self.chooseimage, ds_mounts[journal]['id'], DATASTORE)
        self.insert(self.__journalbtn, -1)
        self.__journalbtn.show()

        # show pendrive button only if pendrive is mounted
        if pendrive > -1:
            self.__pendrivebutton = ToolButton('media-flash-usb')
            self.__pendrivebutton.set_tooltip("Choose image")
            self.__pendrivebutton.connect(
                'clicked',
                self.chooseimage,
                ds_mounts[pendrive]['id'],
                ds_mounts[pendrive]['title'])
            self.insert(self.__pendrivebutton, -1)
            self.__pendrivebutton.show()

        # deck title display and edit
        self.__decktitle_item = Gtk.ToolItem()

        self.__decktitle = Gtk.Entry()
        try:
            title = self.deck.get_title()
        except BaseException:
            title = ""
        print 'self.__decktitle.set_text', title
        self.__decktitle.set_text(title)
        self.__decktitle.set_alignment(0)
        self.__decktitle.connect('activate', self.decktitle_change_cb)
        #self.deck.connect('decktitle_changed', self.decktitle_change_cb)

        self.__decktitle.set_width_chars(20)

        self.__decktitle_item.add(self.__decktitle)
        self.__decktitle.show()

        self.insert(self.__decktitle_item, -1)
        self.__decktitle_item.show()

        # slide title display and edit
        self.__slidetitle_item = Gtk.ToolItem()

        self.__slidetitle = Gtk.Entry()
        self.__slidetitle.set_text("Slide 0")
        self.__slidetitle.set_alignment(0)
        self.__slidetitle.connect('activate', self.slidetitle_change_cb)
        self.deck.connect('slide-redraw', self.slidetitle_changed_cb)

        self.__slidetitle.set_width_chars(20)

        self.__slidetitle_item.add(self.__slidetitle)
        self.__slidetitle.show()

        self.insert(self.__slidetitle_item, -1)
        self.__slidetitle_item.show()

        # separator between presentation buttons and help button
        separator = Gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        #self.__helpbtn = ToolButton('help-button')
        #self.__helpbtn.set_tooltip("Select help presentation")
        #self.__helpbtn.connect('clicked', self.help)
        #self.insert(self.__helpbtn, -1)
        # self.__helpbtn.show()

        #self.__reloadbtn = ToolButton()
        # self.__reloadbtn.set_icon_name('green-button')
        #self.__reloadbtn.connect('clicked', self.reload)
        #self.insert(self.__reloadbtn, -1)
        # self.__reloadbtn.show()

        self.show()

    def decktitle_change_cb(self, widget):
        self.deck.set_title(self.__decktitle.get_text())

    def decktitle_set_new(self, title):
        self.__decktitle.set_text(title)

    def slidetitle_change_cb(self, widget):
        self.deck.set_SlideTitle(self.__slidetitle.get_text())

    def slidetitle_changed_cb(self, widget):
        self.__slidetitle.set_text(self.deck.get_SlideTitle())

    def new(self, widget):
        print 'New slideshow'
        # no effect if slideshow is already 'new', e.g. when ShowNTell is opened
        # directly not by read_file
        # this needs to be changed to show slideshow with html title slide
        self.activity.read_file(
            path(
                activity.get_bundle_path()) /
            'resources' /
            'new.cpxo')

    def open(self, widget):
        print 'Open slideshow'
        scrn3 = self.activity.set_screen(2)
        treeview = scrn3.get_treeView()
        print 'set_cpxo_store'
        treeview.set_model(scrn3.set_store("datastore"))
        print 'slideshow treeview model set'

    def help(self, widget):
        scrn3 = self.activity.set_screen(2)
        # here select help.cpxo in resources
        fn = path(activity.get_bundle_path()) / 'resources' / 'help.cpxo'
        self.activity.read_file(fn)

    def chooseimage(self, widget, source, pth):
        scrn2 = self.activity.set_screen(1)
        treeview = scrn2.get_treeView()
        treeview.set_model(scrn2.set_store(source, pth))

    def reload(self, widget):
        self.deck.reload()

    def showhtml(self, widget):
        self.activity.set_screen(4)
        # intended to show listview of available html templates/slides
        # future feature, not implemented
