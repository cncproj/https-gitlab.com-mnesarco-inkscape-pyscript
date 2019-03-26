# -*- coding: utf-8 -*-
"""
main.py
pyscript core inkscape extension.

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

import inkex, copy, ast, sys, traceback
from pyscript import ui, svg

version = "0.1"

class PYScriptExceptionInfo(object):
    def __init__(self, lineno, message):
        self.lineno = lineno
        self.message = message

class PYScriptInfo(object):

    def __init__(self, node):
        self.node = node
        self.id = node.attrib['id']
        self.label = self.id[9:] if self.id.startswith('pyscript_') else self.id
        self.is_main = self.id == 'pyscript_main'

    def source(self, source = None):
        if source is not None:
            self.node.text = source
        return self.node.text

    def compile(self):
        try:
            ast.parse(self.source(), self.label)
            return [True, self, None]
        except SyntaxError as err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            line_number = err.lineno
            message = "%s at line %d of %s: %s" % (error_class, line_number, self.label, detail)
            return [False, self, PYScriptExceptionInfo(lineno=line_number, message=message)]

    def execute(self, gctx, lctx):
        try:
            exec(self.source(), gctx, lctx)            
            return [True, self, None]
        except SyntaxError as err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            line_number = err.lineno
        except Exception as err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            cl, exc, tb = sys.exc_info()
            line_number = traceback.extract_tb(tb)[-1][1]
            del(cl, exc, tb)
        message = "%s at line %d of %s: %s" % (error_class, line_number, self.label, detail)
        return [False, self, PYScriptExceptionInfo(lineno=line_number, message=message)]

class PYScript(inkex.Effect):

    def __init__(self, edit = True):
        inkex.Effect.__init__(self)
        self.__edit = edit
        self.scripts = dict()

    def create_script(self, sid = 'pyscript_main'):
        root = self.document.getroot()
        node = inkex.etree.SubElement(root, 'script', {'id' : sid, 'type': 'text/python'})
        script = PYScriptInfo(node)
        script.source("\n".join(['# Script: %s' % script.label,
            '"""', 
            'Extension: pyscript v%s <by Frank D. Martinez>' % version,
            'You can write valid python code here.',
            'Your code will be embedded into the document.',
            'Help: https://github.com/mnesarco/inkscape-pyscript',
            '"""']))
        self.scripts[script.id] = script
        return script

    def register_script(self, node):
        script = PYScriptInfo(node)
        self.scripts[script.id] = script
        return script

    def get_all_script_nodes(self):
        root = self.document.getroot()
        nodes = self.document.xpath('//svg:script[@type="text/python"]', namespaces=inkex.NSS)
        if len(nodes) == 0:
            nodes = self.document.xpath('//script[@type="text/python"]', namespaces=inkex.NSS)
        return nodes

    def save_state(self):
        return copy.deepcopy(self.document)

    def restore_state(self, state):
        self.document = state
        self.__reload()

    def __reload(self):
        self.scripts = dict()
        for node in self.get_all_script_nodes():
            self.register_script(node)
        if not ('pyscript_main' in self.scripts):
            self.create_script()

    def compile(self):
        ok = True
        results = []
        for sid, script in self.scripts.items():
            r = script.compile()
            results.append(r)
            ok = ok and r[0]
        return (ok, results)

    def execute(self):
        ok, results = self.compile()
        if ok: 
            saved = self.save_state()
            smain = None
            ctx = {'ink' : self}
            sresults = []
            for sid, script in self.scripts.items():
                if script.is_main:
                    smain = script
                else:
                    r = script.execute(ctx, ctx)
                    sresults.append(r)
                    ok = ok and r[0]
            if ok and (smain is not None):
                r = smain.execute(ctx, ctx)
                sresults.append(r)
                ok = ok and r[0]
            if not ok:
                self.restore_state(saved)  
            return (ok, sresults)
        else:
            return (ok, results)

    def effect(self):
        self.__reload()
        if self.__edit:
            ide = ui.MainWindow(self)
            ide.show()
        else:
            self.run()

    def run(self):
        (ok, results) = self.execute()
        if not ok:
            for (ok, script, err) in results:
                if not ok:
                    inkex.errormsg(err.message)
