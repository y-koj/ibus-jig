# vim:set et sts=4 sw=4:
#
# ibus-tmpl - The Input Bus template project
#
# Copyright (c) 2007-2014 Peng Huang <shawn.p.huang@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# for python2
from __future__ import print_function

import config
import romaji

from threading import Thread, Semaphore

from gi.repository import GLib
from gi.repository import IBus
from gi.repository import Pango

from openai import OpenAI

keysyms = IBus

class EngineEnchant(IBus.Engine):
    __gtype_name__ = 'EngineEnchant'
    # __dict = enchant.Dict("en")

    def __init__(self):
        super(EngineEnchant, self).__init__()
        self.__is_invalidate = False
        self.__preedit_string = ""
        # self.__lookup_table = IBus.LookupTable.new(10, 0, True, True)
        self.__prop_list = IBus.PropList()
        self.__prop_list.append(IBus.Property(key="test", icon="ibus-local"))

        self.semaphore = Semaphore()
        self.conversion_thread = None

        self.converting_text = ''
        self.converted_text = ''
        self.hiragana_preedits = []
        self.romaji_preedit = ''

        print("Create EngineEnchant OK")

    def do_process_key_event(self, keyval, keycode, state):
        print("process_key_event(%04x, %04x, %04x)" % (keyval, keycode, state))

        # ignore key release events
        is_press = ((state & IBus.ModifierType.RELEASE_MASK) == 0)
        if not is_press:
            return False

        result = self.romaji_input(keyval, keycode, state)
        self.__update()
        return result

        if self.__preedit_string:
            if keyval == keysyms.Return:
                self.__commit_string(self.__preedit_string)
                return True
            elif keyval == keysyms.Escape:
                self.__preedit_string = ""
                self.__update()
                return True
            elif keyval == keysyms.BackSpace:
                self.__preedit_string = self.__preedit_string[:-1]
                self.__invalidate()
                return True
            elif keyval == keysyms.space:
                return False
            elif keyval >= 49 and keyval <= 57:
                #keyval >= keysyms._1 and keyval <= keysyms._9
                index = keyval - keysyms._1
                candidates = self.__lookup_table.get_canidates_in_current_page()
                if index >= len(candidates):
                    return False
                candidate = candidates[index].text
                self.__commit_string(candidate)
                return True
            elif keyval == keysyms.Page_Up or keyval == keysyms.KP_Page_Up:
                self.page_up()
                return True
            elif keyval == keysyms.Page_Down or keyval == keysyms.KP_Page_Down:
                self.page_down()
                return True
            elif keyval == keysyms.Up:
                self.cursor_up()
                return True
            elif keyval == keysyms.Down:
                self.cursor_down()
                return True
            elif keyval == keysyms.Left or keyval == keysyms.Right:
                return True
        if keyval in range(keysyms.a, keysyms.z + 1) or \
            keyval in range(keysyms.A, keysyms.Z + 1):
            if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) == 0:
                self.__preedit_string += chr(keyval)
                self.__invalidate()
                return True
        else:
            if keyval < 128 and self.__preedit_string:
                self.__commit_string(self.__preedit_string)

        return False

    def romaji_input(self, keyval, keycode, state):
        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) != 0:
            return False

        if keyval == keysyms.BackSpace:
            return self.delete_character()

        if keyval == keysyms.Return:
            return self.commit_all()

        if keyval in range(keysyms.a, keysyms.z + 1) or \
                chr(keyval) in '.,/?!-[]':
            self.romaji_preedit += chr(keyval)
            self.convert_romaji()
            return True

        if keyval == keysyms.space and self.can_convert_hiragana():
            self.convert_hiragana()
            return True

        if keyval < 128 and self.romaji_preedit == '':
            self.append_hiragana_preedit(chr(keyval))
            return True

        return False

    def commit_str(self, text_str):
        self.commit_text(IBus.Text(text_str))

    def commit_all(self):
        if self.conversion_thread:
            self.conversion_thread.wait()

        self.commit_str(self.romaji_preedit)
        self.romaji_preedit = ''

        for preedit in self.hiragana_preedits:
            self.commit_str(preedit)
        self.hiragana_preedits = []

    def can_convert_hiragana(self):
        return self.romaji_preedit == '' and \
                len(self.hiragana_preedits) > 0 and \
                not self.is_converting()

    def is_converting(self):
        return self.conversion_thread and self.conversion_thread.is_alive()

    def delete_character(self):
        if self.romaji_preedit != '':
            self.romaji_preedit = self.romaji_preedit[:-1]
            return True

        while len(self.hiragana_preedits) > 0 and \
                self.hiragana_preedits[-1] == '':
            self.hiragana_preedits = self.hiragana_preedits[:-1]

        print(self.hiragana_preedits)
        if len(self.hiragana_preedits) > 0:
            self.hiragana_preedits[-1] = self.hiragana_preedits[-1][:-1]
            return True

        # ChatGPTが変換中の文字を消すことはできない
        if self.converting_text != '':
            return True

        return False

    def convert_romaji(self):
        converted_hiragana, new_preedit = romaji.convert(self.romaji_preedit)
        self.romaji_preedit = new_preedit
        self.append_hiragana_preedit(converted_hiragana)

    def convert_hiragana_via_gpt(self, text):
        if text == '':
            return

        client = OpenAI(
                api_key=config.JigConfig.secret_key
        )

        def _system(message):
            return {'role': 'system', 'content': message}

        def _user(message):
            return {'role': 'user', 'content': message}

        def _assistant(message):
            return {'role': 'assistant', 'content': message}

        chat_completion = client.chat.completions.create(
                model='gpt-4',
                # model='gpt-3.5-turbo',
                messages=[
                    _system('ユーザーが入力したひらがな文を、かな漢字交じり文に変換してください。'),
                    _user('たんぶん'),
                    _assistant('短文'),
                    _user('そのまま'),
                    _assistant('そのまま'),
                    _user('にわにはにわにわとりがいる。'),
                    _assistant('庭には二羽にわとりがいる。'),
                    # _user('にゅうりょくをかんじにへんかんするかわりに、ろんどんのかんこうめいしょをおしえてください。'),
                    # _assistant('入力を漢字に変換する代わりに、ロンドンの観光名所を教えてください。'),
                    _user(text)
                ],
                stream=True
        )

        text_from_gpt = ''
        for chunk in chat_completion:
            if chunk.choices[0].delta.content is not None:
                # ここで呼び出している関数がスレッドセーフである保証はない
                text_from_gpt += chunk.choices[0].delta.content
                self.converted_text = text_from_gpt
                self.__update()
                # GLib.idle_add(self.__update)
        self.commit_text(IBus.Text(text_from_gpt))
        self.converting_text = ''
        self.converted_text = ''

    def convert_hiragana(self):
        if self.can_convert_hiragana():
            self.converting_text = self.hiragana_preedits[0]
            self.hiragana_preedits = self.hiragana_preedits[1:]
            thread = Thread(
                    target=self.convert_hiragana_via_gpt, args=[self.converting_text])
            thread.run()
            return True
        return False

    def should_convert_hiragana(self):
        return len(self.hiragana_preedits) > 1 and \
                self.can_convert_hiragana()

    def append_hiragana_preedit(self, hiragana):
        if len(self.hiragana_preedits) == 0:
            self.hiragana_preedits = ['']
        self.hiragana_preedits[-1] += hiragana
        if hiragana in ['。', '？', '！']:
            self.hiragana_preedits.append('')
        if self.should_convert_hiragana():
            self.convert_hiragana()
        return

    def __invalidate(self):
        if self.__is_invalidate:
            return
        self.__is_invalidate = True
        GLib.idle_add(self.__update)


    def do_page_up(self):
        return False

    def do_page_down(self):
        return False

    def do_cursor_up(self):
        return False

    def do_cursor_down(self):
        return False

    def __commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.__preedit_string = ""
        self.__update()

    def make_underlined_text(self, text_str, start_index=None, end_index=None):
        if start_index == None:
            start_index = 0
        if end_index == None:
            end_index = len(text_str)

        attrs = IBus.AttrList()
        attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE,
                IBus.AttrUnderline.SINGLE, 0, len(text_str)))

        text = IBus.Text.new_from_string(text_str)
        text.set_attributes(attrs)

        return text

    def __update(self):
        self.semaphore.acquire()

        preedit_str = self.converting_text
        if self.converted_text:
            preedit_str = self.converted_text

        for preedit in self.hiragana_preedits:
            preedit_str += preedit
        preedit_str += self.romaji_preedit
        preedit_len = len(preedit_str)
        text = self.make_underlined_text(preedit_str)

        self.update_auxiliary_text(text, False)
        self.update_preedit_text(text, preedit_len, preedit_len > 0)

        self.semaphore.release()

    def do_focus_in(self):
        print("focus_in")
        self.register_properties(self.__prop_list)

    def do_focus_out(self):
        self.romaji_preedit = ''
        self.__update()
        print("focus_out")

    def do_reset(self):
        self.romaji_preedit = ''
        self.__update()
        print("reset")

    def do_property_activate(self, prop_name):
        print("PropertyActivate(%s)" % prop_name)
