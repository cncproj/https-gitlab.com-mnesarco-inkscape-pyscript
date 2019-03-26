# -*- coding: utf-8 -*-
"""
ui.py
pyscript ui module.

Copyright (C) 2019 Frank Martinez <mnesarco at gmail.com>

This file is part of inkscape-pyscript.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')

from os.path import join
from gi.repository import Gtk, GtkSource, GObject
import ast, sys
from pyscript import PYSCRIPT_DIR, svg
import inkex

def inputbox(parent, title, subtitle, prompt):
    builder = Gtk.Builder()
    builder.add_from_file(join(PYSCRIPT_DIR, 'inputbox.glade'))
    dialog = builder.get_object('dialog')
    label = builder.get_object('label')
    sub = builder.get_object('subtitle')
    entry = builder.get_object('entry')
    ok = builder.get_object('ok_button')
    cancel = builder.get_object('cancel_button')
    def inputbox_resp(entry, dialog, response):
        dialog.response(response)
    entry.connect('activate', inputbox_resp, dialog, Gtk.ResponseType.OK)
    ok.connect('clicked', inputbox_resp, dialog, Gtk.ResponseType.OK)
    cancel.connect('clicked', inputbox_resp, dialog, Gtk.ResponseType.CANCEL)
    label.set_text("%s:" % prompt)
    sub.set_markup(subtitle)
    dialog.set_transient_for(parent)
    dialog.set_title(title)
    dialog.show_all()
    response = dialog.run()
    name = entry.get_text().strip()
    dialog.destroy()
    if response == int(Gtk.ResponseType.OK) and name != '':
        return name.lower()
    else:
        return None

class MainWindow(object):

    def __init__(self, ext):
        self.ext = ext
        self.current_script = 'pyscript_main'
        self.__build_ui__()
        self.__init_editor__()
        self.__init_tree__()
        self.__init_wnd__()
        self.action_compile(None)
        
    def __build_ui__(self):
        builder = Gtk.Builder()
        try:
            builder.add_from_file(join(PYSCRIPT_DIR, 'code_editor.glade'))        
            self.builder = builder
            self.editor = builder.get_object('source_view')
            self.tree = builder.get_object('scripts_tree')
            self.wnd = builder.get_object('editor_window')
            self.scripts_store = builder.get_object('scripts_store')
            self.console = builder.get_object('console_view')
            notice = builder.get_object('notice')
            notice.set_markup("<b>(C) Copyright 2019 Frank D. Martinez.</b>  <i>Licensed under GNU General Public License.</i>")
        except Exception as e:
            inkex.errormsg(str(e))
            sys.exit(-1)

    def __init_editor__(self):
        lm = GtkSource.LanguageManager()
        self.editor.get_buffer().set_language(lm.get_language('python'))
        self.editor.get_buffer().connect('changed', self.editor_on_changed)

    def __init_tree__(self):
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Name", renderer, text=0)
        self.tree.append_column(col)
        for sid, script in self.ext.scripts.items():
            if script.is_main:
                self.scripts_store.append([ script.label, sid ])
            else:
                self.scripts_store.prepend([ script.label, sid ])
        self.tree.get_selection().connect('changed', self.tree_on_selection_changed)
        n = len(self.ext.scripts) 
        if n > 0:
            self.tree.set_cursor(n-1)

    def __init_wnd__(self):
        self.wnd.connect('destroy', Gtk.main_quit)
        comp = self.builder.get_object('action_compile')
        comp.connect('activate', self.action_compile)
        run = self.builder.get_object('action_run')
        run.connect('activate', self.action_run)
        cancel = self.builder.get_object('action_cancel')
        cancel.connect('activate', self.action_cancel)
        add = self.builder.get_object('action_add_script')
        add.connect('activate', self.action_add_script)

    def get_current(self):
        if self.current_script is None:
            return None
        else:
            return self.ext.scripts[self.current_script]

    def goto_line(self, lineno):
        buffer = self.editor.get_buffer()
        iterator = buffer.get_iter_at_line(lineno-1)
        buffer.place_cursor(iterator)
        self.editor.scroll_to_iter(iterator, 0, False, 0.5, 0.5)

    def editor_on_changed(self, widget):
        current = self.get_current()
        if current is not None:
            current.source(self.get_editor_text())

    def action_add_script(self, widget):
        name = inputbox(self.wnd, "New Script", ("Insert new named script into the document.\n"
        "All scripts are executed before <b>main</b> but there are no other execution order "
        "guarantees"), "Name")
        if name is not None:
            name = name.lower()
            sid = name if name.startswith('pyscript_') else 'pyscript_' + name
            if sid in self.ext.scripts:
                for i in range(0, len(self.scripts_store)):
                    if self.scripts_store[i][1] == sid:
                        self.tree.set_cursor(i)
                        return
            else:
                script = self.ext.create_script(sid)
                self.scripts_store.prepend([script.label, script.id])
                self.tree.set_cursor(0)

    def action_compile(self, widget):
        self.log("Python %s" % sys.version)
        (ok, results) = self.ext.compile()
        for ok, script, err in results:
            if ok:
                self.log("%s Compiled [Ok]" % script.label)
            else:
                self.log(err.message)
                if script.id == self.current_script:
                    self.exception_to_line(err)

    def action_run(self, widget):
        (ok, results) = self.ext.execute()
        if ok:
            self.close()
        else:
            for ok, script, err in results:
                if not ok:
                    self.log(err.message)
                    if script.id == self.current_script:
                        self.exception_to_line(err)

    def exception_to_line(self, ex):
        if hasattr(ex, 'lineno'):
            self.goto_line(ex.lineno)

    def action_cancel(self, widget):
        if self.confirm("Are you sure you want to discard all changes?"):
            self.ext.document = self.ext.original_document
            self.close()

    def close(self):
        self.wnd.destroy()

    def show(self):
        try:
            self.wnd.show_all()
            self.wnd.maximize()
            Gtk.main()
        except Exception as e:
            inkex.errormsg(str(e))

    def tree_get_selected_id(self):
        model, treeiter = self.tree.get_selection().get_selected()
        if treeiter is None:
            return None
        else:
            return model[treeiter][1]            

    def tree_on_selection_changed(self, selection):
        sid = self.tree_get_selected_id()
        if sid:
            script = self.ext.scripts[sid]
            if script is None:
                pass
            else:
                self.edit_node(script)
        return True

    def get_editor_text(self):
        buffer = self.editor.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        return buffer.get_text(start, end, True)

    def edit_node(self, script):
        self.current_script = script.id
        source = script.source()
        self.editor.get_buffer().set_text("" if source is None else source)

    def log(self, text):
        buffer = self.console.get_buffer()
        end = buffer.get_end_iter()
        buffer.insert(end, str(text) + "\n")
        self.console.scroll_to_mark(buffer.get_insert(), 0, True, 0.5, 0.5)

    def confirm(self, prompt):
        dlg = Gtk.MessageDialog(transient_for=self.wnd, modal=True, buttons=Gtk.ButtonsType.OK_CANCEL)
        dlg.props.text = prompt 
        response = dlg.run()
        dlg.destroy()
        return response == Gtk.ResponseType.OK       

