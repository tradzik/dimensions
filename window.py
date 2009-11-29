#Copyright (c) 2009, Walter Bender
#Copyright (c) 2009, Michele Pratusevich
#Copyright (c) 2009, Vincent Le

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import pygtk
pygtk.require('2.0')
import gtk
from gettext import gettext as _

try:
   from sugar.graphics import style
   GRID_CELL_SIZE = style.GRID_CELL_SIZE
except:
   GRID_CELL_SIZE = 0

from grid import *
from card import *

from math import sqrt

CARD_W = 55
CARD_H = 125

class taWindow: pass

#
# handle launch from both within and without of Sugar environment
#
def new_window(canvas, path, parent=None):
   tw = taWindow()
   tw.path = path
   tw.activity = parent

   # starting from command line
   # we have to do all the work that was done in CardSortActivity.py
   if parent is None:
       tw.sugar = False
       tw.canvas = canvas

   # starting from Sugar
   else:
       tw.sugar = True
       tw.canvas = canvas
       parent.show_all()

   tw.canvas.set_flags(gtk.CAN_FOCUS)
   tw.canvas.add_events(gtk.gdk.BUTTON_PRESS_MASK)
   tw.canvas.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
   tw.canvas.connect("expose-event", _expose_cb, tw)
   tw.canvas.connect("button-press-event", _button_press_cb, tw)
   tw.canvas.connect("button-release-event", _button_release_cb, tw)
   tw.canvas.connect("key_press_event", _keypress_cb, tw)
   tw.width = gtk.gdk.screen_width()
   tw.height = gtk.gdk.screen_height()-GRID_CELL_SIZE
   tw.card_w = CARD_W
   tw.card_h = CARD_H
   tw.scale = 0.8 * tw.height/(tw.card_h*3)
   tw.area = tw.canvas.window
   tw.gc = tw.area.new_gc()
   tw.cm = tw.gc.get_colormap()
   tw.msgcolor = tw.cm.alloc_color('black')
   tw.sprites = []
   tw.selected = []

   # create a deck of cards, shuffle, and then deal
   tw.deck = Grid(tw)
   tw.deck.shuffle()
   tw.deck.deal(tw)
   tw.matches = 0
   tw.msg = ""

   # initialize three card-selected overlays
   for i in range(0,3):
       tw.selected.append(Card(tw,-1,0,0,0))

   # make an array of three cards that are clicked
   tw.clicked = [None, None, None]

   # Start doing something
   tw.keypress = ""
   tw.press = -1
   tw.release = -1
   tw.start_drag = [0,0]

   return tw

#
# Button press
#
def _button_press_cb(win, event, tw):
   win.grab_focus()
   x, y = map(int, event.get_coords())
   tw.start_drag = [x,y]
   spr = findsprite(tw,(x,y))
   if spr is None:
       tw.press = None
       tw.release = None
       return True
   # take note of card under button press
   tw.press = spr
   return True

#
# Button release, where all the work is done
#
def _button_release_cb(win, event, tw):
   win.grab_focus()
   x, y = map(int, event.get_coords())
   spr = findsprite(tw,(x,y))
   if spr is None:
       tw.press = None
       tw.release = None
       return True
   # take note of card under button release
   tw.release = spr

   # check to make sure a card in the matched pile isn't selected
   if spr.x == 10:
      return True

   # check to make sure that the current card isn't already selected
   for a in tw.clicked:
       if a is spr:
           return True

   # add the selected card to the list
   # and show the selection mask
   for a in tw.clicked:
       if a is None:
           i = tw.clicked.index(a)
           tw.clicked[i] = spr
           tw.selected[i].spr.x = spr.x
           tw.selected[i].spr.y = spr.y
           tw.selected[i].show_card()
           break # we only want to add the card to the list once

   # if we have three cards selected, test for a set
   #check to see if it's a set
   try:
       tw.clicked.index(None)
   except ValueError:
       if match_check([tw.deck.spr_to_card(tw.clicked[0]),
                     tw.deck.spr_to_card(tw.clicked[1]),
                     tw.deck.spr_to_card(tw.clicked[2])]):
           if tw.deck.remove_and_replace(tw.clicked, tw) is None:
               tw.activity.deck_label.set_text(_("The deck is empty."))
           else:
               tw.activity.deck_label.set_text(
                   _("%d cards remain in the deck") % \
                  (tw.deck.count-tw.deck.index))
           tw.matches += 1
           tw.activity.status_label.set_text(_("Found a match."))
           if tw.matches == 1:
               tw.activity.match_label.set_text(
                  _("%d match found.") % (tw.matches))
           else:
               tw.activity.match_label.set_text(
                  _("%d matches found.") % (tw.matches))

       else:
           tw.activity.status_label.set_text(_("Not a match."))
       tw.clicked = [None, None, None]
       for a in tw.selected:
           a.hide_card()
   return True

#
# Keypress
#
def _keypress_cb(area, event, tw):
   tw.keypress = gtk.gdk.keyval_name(event.keyval)
   return True

#
# Repaint
#
def _expose_cb(win, event, tw):
   redrawsprites(tw)
   return True

#
# callbacks
#
def _destroy_cb(win, event, tw):
   gtk.main_quit()


#
# Check to see whether there are any matches on the board
#
def find_a_match(tw):
    a = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14]
    for i in Permutation(a): # really should be Combination
        cardarray = [tw.deck.grid[i[0]],tw.deck.grid[i[1]],tw.deck.grid[i[2]]]
        if match_check(cardarray) is True:
            tw.msg = str(i)
            return True
    return False

#
# Check whether three cards are a match based on the criteria that
# in all characteristics:
# either all cards are the same of all cards are different
#
def match_check(cardarray):
   for a in cardarray:
       if a is None:
           return False

   if (cardarray[0].num + cardarray[1].num + cardarray[2].num)%3 != 0:
      return False
   if (cardarray[0].fill + cardarray[1].fill + cardarray[2].fill)%3 != 0:
      return False
   if (cardarray[0].shape + cardarray[1].shape + cardarray[2].shape)%3 != 0:
      return False
   if cardarray[0].color == cardarray[1].color and \
      cardarray[1].color != cardarray[2].color:
      return False
   if cardarray[0].color != cardarray[1].color and \
      cardarray[1].color != cardarray[2].color and \
      cardarray[0].color == cardarray[2].color:
      return False
   if cardarray[0].color != cardarray[1].color and \
      cardarray[1].color == cardarray[2].color and \
      cardarray[0].color != cardarray[2].color:
      return False
   if cardarray[0].color == cardarray[1].color and \
      cardarray[1].color == cardarray[2].color and \
      cardarray[0].color != cardarray[2].color:
      return False
   return True

#
# Permutaion class for checking for all possible matches on the grid
#    
class Permutation: 
    def __init__(self, justalist): 
        self._data = justalist[:] 
        self._sofar = [] 
    def __iter__(self): 
        return self.next() 
    def next(self): 
         for elem in self._data: 
             if elem not in self._sofar: 
                 self._sofar.append(elem) 
                 if len(self._sofar) == 3: 
                     yield self._sofar[:] 
                 else: 
                     for v in self.next(): 
                         yield v 
                 self._sofar.pop() 

