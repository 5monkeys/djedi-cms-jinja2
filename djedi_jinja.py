"""Jinja2 implementations of the Djedi template tags."""

import textwrap

import cio

from djedi.templatetags.djedi_tags import render_node
from jinja2 import Markup, nodes
from jinja2.ext import Extension

__all__ = ['NodeExtension', 'node']


class NodeExtension(Extension):
    """Block version of the `node` function."""
    tags = set(['blocknode'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        uri = parser.parse_expression()

        params = []
        # Parse extra variables to be used for formatting.
        while parser.stream.current.type != 'block_end':
            if params:
                parser.stream.expect('comma')

            target = parser.parse_assign_target(name_only=True)
            parser.stream.expect('assign')
            value = parser.parse_expression()
            params.append(nodes.Pair(nodes.Const(target.name), value))

        args = [uri, nodes.Dict(params)]
        body = parser.parse_statements(['name:endblocknode'], drop_needle=True)

        return nodes.CallBlock(
            self.call_method('_render_node', args=args),
            [], [], body
        ).set_lineno(lineno)

    def _render_node(self, uri, params, caller):
        default = caller()
        default = default.strip('\n\r')
        default = textwrap.dedent(default)
        edit = params.pop('edit', True)
        return node(uri, default=default, edit=edit, context=params)


def node(uri, default=None, edit=True, context=None):
    """Function that renders a Djedi node."""
    node = cio.get(uri, default=default or u'')
    return Markup(render_node(node, edit=edit, context=context))
