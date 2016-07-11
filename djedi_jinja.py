"""Jinja2 implementations of the Djedi template tags."""

import hashlib
import textwrap

import cio

from djedi.templatetags.djedi_tags import render_node

from jinja2 import Markup, nodes
from jinja2.ext import Extension
from jinja2.lexer import Token

__all__ = ['NodeExtension', 'node']
__version__ = '2.0.2'
__author__ = 'Christopher Rosell <chrippa@5monkeys.se>'
__authors__ = ['Christopher Rosell', 'Andrei Fokau', 'Simon Lydell']


DJEDI_TAG = 'node'
DJEDI_BLOCK_TAG = 'blocknode'
DJEDI_INIT_TAG = '__djedi__init__'
DJEDI_NODE_STORAGE = '__djedi_nodes__'


class Builtin(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


DJEDI_NODE_STORAGE_NODE = (
    nodes.If(
        # if not isinstance(DJEDI_NODE_STORAGE, dict):
        nodes.Not(
            nodes.Call(
                nodes.Const(Builtin('isinstance')),
                [
                    nodes.Name(DJEDI_NODE_STORAGE, 'load'),
                    nodes.Const(Builtin('dict')),
                ], [], None, None
            )
        ),
        # DJEDI_NODE_STORAGE = {}
        [
            nodes.Assign(
                nodes.Name(DJEDI_NODE_STORAGE, 'store'),
                nodes.Dict([])
            ),
        ],
        # else: pass
        []
    )
)


class NodeExtension(Extension):
    tags = set([DJEDI_INIT_TAG, DJEDI_TAG, DJEDI_BLOCK_TAG])

    def create_node_id(self, uri, default):
        m = hashlib.sha256()
        m.update(uri.encode('utf8'))
        if default:
            m.update(default.encode('utf8'))
        return m.hexdigest()

    def create_tuple(self, *values, **kwargs):
        ctx = kwargs.get('ctx', 'local')
        node = kwargs.get('node', nodes.Const)
        node_args = kwargs.get('node_args', [])
        values = [node(v, *node_args) if isinstance(v, str) else v for v in values]
        return nodes.Tuple(values, ctx)

    def create_node_storage(self):
        # Keep reference to allow adding nodes during parsing
        self._node_storage = []

        create_nodes = nodes.Assign(
            nodes.Name('__', 'local'),
            self.call_method(
                '_create_nodes',
                [
                    nodes.Name(DJEDI_NODE_STORAGE, 'load'),
                    nodes.List(self._node_storage),
                ]
            )
        )
        return [DJEDI_NODE_STORAGE_NODE, create_nodes]

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

    def buffer_node(self, parser, uri, default):
        node_id = self.create_node_id(uri.value, default.value)
        for node in self._node_storage:
            if node.items[0].value == node_id:
                break
        else:
            self._node_storage.append(self.create_tuple(node_id, uri, default))

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
            return [node.set_lineno(lineno) for node in self.create_node_storage()]

        # Parse arguments
        uri = parser.parse_expression()
        params = self.parse_params(parser)
        body = []

        # If this is a blocknode, parse the body too.
        if tag == DJEDI_BLOCK_TAG:
            body = parser.parse_statements(['name:end{}'.format(DJEDI_BLOCK_TAG)], drop_needle=True)
            if body:
                default = body[0].nodes[0].data.rstrip('\n\r ')
                default = textwrap.dedent(default)
                default = nodes.Const(default)
            else:
                default = nodes.Const(None)
        else:
            default = params.pop('default', nodes.Const(None))
        edit = params.pop('edit', nodes.Const(True))

        # If we got passed const values, we can buffer nodes before render.
        can_buffer = all([isinstance(n, nodes.Const) for n in (uri, default)])
        if can_buffer:
            node_or_uri = self.buffer_node(parser, uri, default)
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

    def _create_nodes(self, nodes, local_nodes):
        for node_id, uri, default in local_nodes:
            if node_id not in nodes:
                nodes[node_id] = cio.get(uri, default=default or '')

    def _render_node(self, node_or_uri, default, edit, params, tag, caller):
        if isinstance(node_or_uri, str):
            node = cio.get(node_or_uri, default=default, lazy=False)
        else:
            node = node_or_uri

        return Markup(render_node(node, edit=edit, context=params))


def node(uri, default=None, edit=True, context=None):
    """Function that renders a Djedi node."""
    node = cio.get(uri, default=default or u'', lazy=False)
    return Markup(render_node(node, edit=edit, context=context))
