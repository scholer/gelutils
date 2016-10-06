#!/usr/bin/python
# -*- coding: utf-8 -*-
#    Copyright 2016 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import re
import argparse
from argparse import (HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
                      ArgumentDefaultsHelpFormatter, MetavarTypeHelpFormatter)
from argparse import _StoreAction as StoreAction
from argparse import _StoreTrueAction as StoreTrueAction
from argparse import _CountAction as CountAction

# import gelutils
from gelutils.argutils import make_parser

config_action_types = (StoreAction, StoreTrueAction, CountAction)

# See:
# argparse.py module - is pretty easy to understand.
# github.com/ribozz/sphinx-argparse/
# http://docopt.org/
# http://pythonhosted.org/argh/
# https://pypi.python.org/pypi/argcomplete


"""

Use this module to create Markdown documentation files using the command line / config keyword reference help
already specified in the argutils module.

To use:
# Make sure you are in a python environment where gelutils is available.
$ cd <project root>
$ python docs/docgen.py > docs/Config-Ref.md

"""


def playing_around():
    """
    formatter_class=HelpFormatter
    formatter.add_usage(self.usage, self._actions,
                        self._mutually_exclusive_groups)
    return formatter.format_help()
    :return:
    """

    # Formatters:
    # HelpFormatter - Standard (console) help formatting.
    # RawDescriptionHelpFormatter - Will not touch description.
    # RawTextHelpFormatter - will not touch help format.
    p = make_parser(prog="gui",
                    formatter_class=HelpFormatter)  # RawTextHelpFormatter)

    format_config = dict(
        # indent_increment=2,
        # max_help_position=80,
        # width=1000
    )
    formatter = p.formatter_class(prog=p.prog, **format_config)

    # Disassembled ArgumentParser.format_help:
    formatter.add_usage(usage=p.usage, actions=p._actions,
                        groups=p._mutually_exclusive_groups, prefix=None)
    # add_usage just does:
    # if usage is not SUPPRESS:
    #     args = usage, actions, groups, prefix
    #     self._add_item(self._format_usage, args)
    # and _add_item just does:
    # def _add_item(self, func, args):
    #     self._current_section.items.append((func, args))

    # description:
    formatter.add_text(p.description)

    # positionals, optionals and user-defined groups
    for action_group in p._action_groups:
        formatter.start_section(action_group.title)
        formatter.add_text(action_group.description)
        formatter.add_arguments(action_group._group_actions)
        formatter.end_section()

    # epilog
    formatter.add_text(p.epilog)

    # determine help from format above
    help_text = formatter.format_help()

    # def format_help() does:
    #     help = self._root_section.format_help()
    #     if help:
    #         help = self._long_break_matcher.sub('\n\n', help)
    #         help = help.strip('\n') + '\n'

    # I.e. the actual formatting is done by the section

    print(help_text)

    # p._optionals._actions
    # formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)
    # p._actions


def format_actions_table(actions, prefix="<table>", postfix="</table>",
                         exclude_dest=('file', 'verbose', "config_template", "load_system_config"),
                         action_types=config_action_types,
                         replace_angle_brackets=True):
    """

    :param actions:
    :param prefix:
    :param postfix:
    :param exclude_dest: Exclude these keywords, typically more system-level keywords.
    :param action_types: The action types/classes to include.
    :param replace_angle_brackets: If True, replace "<" and ">" with "&lt;" and "&gt;" HTML codes.
    :return:
    """

    table_strs = [prefix]

    if action_types:
        actions = [a for a in actions if type(a) in action_types and a.dest not in exclude_dest]

    columns = ('dest', 'metavar', 'default', 'help')
    # row_fmt = "<tr>" + "  ".join("<td><pre>{a.%s}</pre></td>" % col for col in columns) + "</tr>"
    # col_fmts = {"dest": "<td><strong>{a.%s}</strong></td>"} # dot-notation
    cell_fmts = {"dest": "<td><strong>{%s}</strong></td>"}
    row_fmt = "<tr>" + "  ".join(cell_fmts.get(col, "<td>{%s}</td>") % col for col in columns) + "</tr>"

    row_fmt = "<tr>  <td><pre>{dest}</pre></td> <td>{metavar}</td> <td>{help} {default}</td>  </tr>"

    # headers = ("Keyword", "Type", "Default", "Help")
    headers = ("Keyword", "Type and default", "Help")
    table_strs.append("<tr>" + "  ".join("<th>%s</th>" % h for h in headers) + "</tr>")

    for a in actions:
        fields = vars(a)

        if fields['metavar'] is None:
            # Default behaviour, only 1 var, or true/false:
            if type(a) is StoreTrueAction:
                fields['metavar'] = "true/false"
            else:
                if type(a) is CountAction:
                    fields['metavar'] = "Integer"
                    a.default = 0
                if a.nargs is None:
                    fields['metavar'] = str(a.type.__name__ if a.type else a.dest)
                elif a.nargs == "?":
                    fields['metavar'] = "<%s> (optional)" % (a.type.__name__ if a.type else a.dest, )
                elif a.nargs == "+":
                    fields['metavar'] = str([a.type.__name__ if a.type else a.dest, "(...)"])
                else:
                    fields['metavar'] = "<%s>" % [a.type.__name__ if a.type else a.dest for _ in range(int(a.nargs))]

        if fields['metavar'] and not isinstance(fields['metavar'], str):
            # fields['metavar'] = "[" + ", ".join(str(v) for v in fields['metavar']) + "]"
            fields['metavar'] = ", ".join(str(v) for v in fields['metavar'])
        fields['metavar'] = fields['metavar'].replace("<", "&lt;").replace(">", "&gt;")

        fields['default'] = "" if fields['default'] is None else "(default: {})".format(fields['default'])

        if fields['help']:
            fields['help'] = fields['help'].strip().replace("\n", " ")
            fields['help'] = re.sub(" +", " ", fields['help'])
            fields['help'] = fields['help'].replace("<", "&lt;").replace(">", "&gt;")
            # Argutils does a % formatting of all help strings. We must do the same to get same behaviour.
            # try:
            fields['help'] = fields['help'] % {}
            # except ValueError as e:
            #     print("Error formatting fields['help']: %s" % e)
            #     print(fields['help'])
            #     import pdb
            #     pdb.set_trace()

        table_strs.append(row_fmt.format(**fields))

    table_strs.append(postfix)

    table_str = "\n".join(table_strs)
    return table_str


def main(argv=None):

    if argv is None:
        argv = sys.argv

    print("argv:", argv)
    script_name = argv[0]
    outputfn = None
    template = None

    if len(argv) > 1:
        outputfn = argv[1]
        if len(argv) > 2:
            template = argv[2]

    p = make_parser(prog="gui")
    # p._optionals._actions
    actions = p._actions

    table_str = format_actions_table(actions)

    if template:
        template_str = open(template).read()
        table_str = template_str % (table_str, )

    if outputfn is None:
        print(table_str)
    else:
        with open(outputfn, 'w') as f:
            if template:
                print("Using template: ", template)
            print("Writing to file:", outputfn)
            f.write(table_str)


if __name__ == "__main__":
    # print(p.format_help())   # long help
    # print(p.format_usage())  # brief usage
    main()
