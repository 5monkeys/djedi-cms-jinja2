Djedi CMS Jinja2
================

This module provides `Jinja2`_ versions of the `Django`_ template tags
provided by `Djedi CMS`_.

djedi_jinja.NodeExtension
--------------------------

Jinja2 extension providing the same functionality and syntax as the
Django tags `node`_ and `blocknode`_.

It also has the following extra bonuses:

-  Intelligently buffers nodes to be able to use ``get_many`` from
   cache, even when Jinja2’s template parsing cache is enabled, unlike
   the Django counterpart.
-  Possible to pass variables as URI argument to allow "dynamic" node
   URIs, though this will make the node unbufferable, so use with care.

djedi_jinja.node
-----------------

Jinja2 global function with the same functionality as the Django tag
`node`_.

Note: As of 2.0 it is recommended to use the ``node`` tag provided by
the extension instead. This is still provided for special cases and
backwards compatibility.

.. _Jinja2: http://jinja.pocoo.org/
.. _Django: http://djangoproject.com/
.. _Djedi CMS: http://djedi-cms.org/
.. _node: http://djedi-cms.org/usage.html#node-tag
.. _blocknode: http://djedi-cms.org/usage.html#blocknode-tag
