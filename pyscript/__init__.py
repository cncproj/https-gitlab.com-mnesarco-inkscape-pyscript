# -*- coding: utf-8 -*-
"""
__init__.py
pyscript module.

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

from gi.repository import Gtk, GtkSource, GObject
from os.path import abspath, dirname, join

PYSCRIPT_DIR = abspath(dirname(__file__))
GObject.type_register(GtkSource.View)

import ui
import svg

__all__ = ['ui', 'svg', 'main']