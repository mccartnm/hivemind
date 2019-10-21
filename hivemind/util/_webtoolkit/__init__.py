"""
Copyright (c) 2019 Michael McCartney, Kevin McLoughlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from aiohttp import web
from .abstract import _Renderable

# -- Build registration ? - not in love with this
from . import card

class API(object):
    """
    Request object for handling basic fetch() api
    with the webfront. Providing a smoother transition
    for the interface.

    This will not be a full featured REST framework - just
    make it as simple as possible to cover omst of the
    cases.
    """

    # 
    categories = {}
    _no_lookup = set()

    def __init__(self):
        pass


    @classmethod
    def register_to_category(cls, category, name, info, **kwargs):
        """
        Register a given item with a category for querying
        """
        cls.categories.setdefault(category, {})[name] = info
        if kwargs.get('no_lookup'):
            cls._no_lookup.add(category)


    @classmethod
    def query_renderable(cls, path, controller, querydict):
        """
        Ask for and render select objects within our ecosystem

        .. code-block:: text

            # General
            /render/cards/topics

            # Specific
            /render/nodecards/nodes/node

        :param path: The url path that dictates what we're rendering
        :param querydict: Dictionary carrying any addition search filters
        :return: web.Response with rendered text
        """
        parts = path.split('/')
        if len(parts) not in (2, 3):
            raise web.HTTPBadRequest()

        renderable_name, category, *spec = parts
        if renderable_name not in _Renderable._simple_registry:
            raise web.HTTPNotFound(text=f'Unkown renderable: {renderable_name}')

        if category not in cls.categories:
            raise web.HTTPNotFound(text=f'Unkown category: {category}')

        renderable = _Renderable._simple_registry[renderable_name]()
        category_to_render = cls.categories[category]

        output = []
        if category in cls._no_lookup:

            if 'name' in querydict:
                # We can search for the specific name of the item
                name = querydict['name']
                if name not in category_to_render:
                    raise web.HTTPNotFound(text=f'Unkown {category}: {name}')
                output.append(renderable.render({'item' : category_to_render[name]}))
            else:
                for name, item in sorted(category_to_render.items()):
                    output.append(renderable.render({'item' : item}))


        else:
            if not spec:
                raise web.HTTPBadRequest()

            if not spec[0] in category_to_render:
                raise web.HTTPNotFound(text=f'Unknown spec: {spec[0]}')

            render_spec = category_to_render[spec[0]]

            # FIXME: Rework for an even more general interface

            if render_spec.get('function', None):
                info = render_spec['function'](
                    controller, querydict
                )
                output = [renderable.render({'item' : x}) for x in info]

        res = {
            'content' : output,
            'count' : len(output)
        }
        return web.json_response(res)


def api_request(path, controller, querydict):
    """
    Run an api request based on the query information
    """
    if path.startswith('render/'):
        return API.query_renderable(path[7:], controller, querydict)
