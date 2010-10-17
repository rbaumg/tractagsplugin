# -*- coding: utf-8 -*-
#
# Copyright (C) 2006 Alec Thomas <alec@swapoff.org>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from genshi.builder import tag as builder

from trac.core import Component, implements
from trac.resource import Resource, get_resource_url, render_resource_link
from trac.util import embedded_numbers
from trac.util.compat import sorted, set
from trac.util.text import to_unicode
from trac.web.chrome import add_stylesheet
from trac.wiki import IWikiMacroProvider

from tractags.api import TagSystem, _


def render_cloud(env, req, cloud, renderer=None):
    """Render a tag cloud

    :cloud: Dictionary of {object: count} representing the cloud.
    :param renderer: A callable with signature (tag, count, percent) used to
                     render the cloud objects.
    """
    min_px = 10.0
    max_px = 30.0
    scale = 1.0

    add_stylesheet(req, 'tags/css/tractags.css')

    if renderer is None:
        def default_renderer(tag, count, percent):
            href = get_resource_url(env, Resource('tag', tag), req.href)
            return builder.a(tag, rel='tag', title='%i' % count, href=href,
                             style='font-size: %ipx' %
                                   int(min_px + percent * (max_px - min_px)))
        renderer = default_renderer

    # A LUT from count to n/len(cloud)
    size_lut = dict([(c, float(i)) for i, c in
                     enumerate(sorted(set([r for r in cloud.values()])))])
    if size_lut:
        scale = 1.0 / len(size_lut)

    ul = builder.ul(class_='tagcloud')
    last = len(cloud) - 1
    for i, (tag, count) in enumerate(sorted(cloud.iteritems())):
        percent = size_lut[count] * scale
        li = builder.li(renderer(tag, count, percent))
        if i == last:
            li(class_='last')
        li()
        ul(li, ' ')
    return ul


class TagWikiMacros(Component):
    """Provides macros, that utilize the tagging system in wiki."""

    implements(IWikiMacroProvider)

    def __init__(self):
        # TRANSLATOR: Keep macro doc style formatting here, please.
        self.doc_cloud = _("""Display a tag cloud.

    Show a tag cloud for all tags on resources matching query.

    Usage:

    {{{
    [[TagCloud(query)]]
    }}}

    See tags documentation for the query syntax.
    """)
        self.doc_listtagged = _("""List tagged resources.

    Usage:

    {{{
    [[ListTagged(query)]]
    }}}

    See tags documentation for the query syntax.
    """)

    # IWikiMacroProvider

    def get_macros(self):
        yield 'ListTagged'
        yield 'TagCloud'

    def get_macro_description(self, name):
        if name == 'ListTagged':
            return self.doc_listtagged
        elif name == 'TagCloud':
            return self.doc_cloud

    def expand_macro(self, formatter, name, content):
        if name == 'TagCloud':
            if not content:
                content = ''
            req = formatter.req
            all_tags = TagSystem(self.env).get_all_tags(req, content)
            return render_cloud(self.env, req, all_tags)

        elif name == 'ListTagged':
            req = formatter.req
            tag_system = TagSystem(self.env)
            query_result = tag_system.query(req, content)
            add_stylesheet(req, 'tags/css/tractags.css')

            def _link(resource):
                return render_resource_link(self.env, formatter.context,
                                            resource, 'compact')

            ul = builder.ul(class_='taglist')
            for resource, tags in sorted(query_result, key=lambda r: \
                                         embedded_numbers(
                                         to_unicode(r[0].id))):
                tags = sorted(tags)

                desc = tag_system.describe_tagged_resource(req, resource)

                if tags:
                    rendered_tags = [
                        _link(resource('tag', tag))
                        for tag in tags
                        ]
                    li = builder.li(_link(resource), ' ', desc, ' (',
                                    rendered_tags[0], [(' ', tag) for \
                                        tag in rendered_tags[1:]], ')')
                else:
                    li = builder.li(_link(resource), ' ', desc)
                ul(li, '\n')
            return ul
