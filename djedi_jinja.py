"""Jinja2 implementations of the Djedi template tags."""

import hashlib
import textwrap

import cio

from djedi.templatetags.djedi_tags import render_node

from jinja2 import Markup, nodes
from jinja2.ext import Extension
from jinja2.lexer import Token

__all__ = ['NodeExtension', 'node']


DJEDI_TAG = 'node'
DJEDI_BLOCK_TAG = 'blocknode'
DJEDI_INIT_TAG = '__djedi__init__'
DJEDI_NODE_STORAGE = '__djedi_nodes__'


class NodeExtension(Extension):
    tags = set([DJEDI_INIT_TAG, DJEDI_TAG, DJEDI_BLOCK_TAG])

    def create_node_id(self, uri, default):
        m = hashlib.sha256()
        m.update(uri.encode('utf8'))
        m.update(default.encode('utf8'))
        return m.hexdigest()

    def parse_params(self, parser):
        params = {}
        while parser.stream.current.type != 'block_end':
            if params:
                parser.stream.expect('comma')

            target = parser.parse_assign_target(name_only=True)
            parser.stream.expect('assign')
            params[target.name] = parser.parse_expression()

        return params

    def filter_stream(self, stream):
        djedi_init = [
            Token(0, 'block_begin', '{%'),
            Token(0, 'name', DJEDI_INIT_TAG),
            Token(0, 'block_end', '%}'),
            Token(0, 'data', '\n')
        ]
        for token in djedi_init:
            yield token

        for token in stream:
            yield token

    def buffer(self, uri, default):
        node_id = self.create_node_id(uri.value, default.value)
        exists = False
        for pair in self._node_storage:
            if pair.key.value == node_id:
                exists = True
                break

        if not exists:
            self._node_storage.append(
                nodes.Pair(
                    nodes.Const(node_id),
                    self.call_method('_create_node', args=[uri, default]),
                )
            )

        return nodes.Getitem(
            nodes.Name(DJEDI_NODE_STORAGE, 'load'),
            nodes.Const(node_id),
            None
        )

    def parse(self, parser):
        # Tag information
        token = next(parser.stream)
        lineno = token.lineno
        tag = token.value

        if tag == DJEDI_INIT_TAG:
            # Keep reference to allow adding nodes during parsing
            self._node_storage = []
            node = nodes.Assign(
                nodes.Name(DJEDI_NODE_STORAGE, 'store'),
                nodes.Dict(self._node_storage).set_lineno(lineno)
            ).set_lineno(lineno)
            return node

        # Parse arguments
        uri = parser.parse_expression()
        params = self.parse_params(parser)
        body = []

        # If this is a blocknode, parse the body too.
        if tag == DJEDI_BLOCK_TAG:
            body = parser.parse_statements(['name:end{}'.format(DJEDI_BLOCK_TAG)], drop_needle=True)
            if body:
                default = nodes.Const(body[0].nodes[0].data)
            else:
                default = nodes.Const(None)
        else:
            default = params.pop('default', nodes.Const(None))
        edit = params.pop('edit', nodes.Const(True))

        # If we got passed const values, we can buffer nodes before render.
        can_buffer = all([isinstance(n, nodes.Const) for n in (uri, default)])
        if can_buffer:
            node_or_uri = self.buffer(uri, default)
        else:
            node_or_uri = uri

        params_dict = nodes.Dict([
            nodes.Pair(nodes.Const(key), value)
            for key, value in params.items()
        ])
        args = [node_or_uri, default, edit, params_dict, nodes.Const(tag)]

        return nodes.CallBlock(
            self.call_method('_render_node', args=args),
            [], [], body
        ).set_lineno(lineno)

    def _create_node(self, uri, default):
        return cio.get(uri, default=default or '')

    def _render_node(self, node_or_uri, default, edit, params, tag, caller):
        if tag == DJEDI_BLOCK_TAG:
            default = caller()
            default = default.strip('\n\r')
            default = textwrap.dedent(default)

        if isinstance(node_or_uri, str):
            node = cio.get(node_or_uri, default=default, lazy=False)
        else:
            node = node_or_uri

        return Markup(render_node(node, edit=edit, context=params))


def node(uri, default=None, edit=True, context=None):
    """Function that renders a Djedi node."""
    node = cio.get(uri, default=default or u'', lazy=False)
    return Markup(render_node(node, edit=edit, context=context))
