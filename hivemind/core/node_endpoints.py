"""
Default node endpoints
"""
from .base import _HandlerBase
import asyncio
from aiohttp import web
import jinja2
import aiohttp_jinja2

class RootNodeHandler(_HandlerBase):
    """
    Endpoints for the rot controller to view and manage
    basic node interactions.
    """

    # -- Template Rendering

    @aiohttp_jinja2.template("nodes/index.html")
    async def nodes(self, request):
        """
        Simple nodes interface
        """
        return self.controller.base_context()


    @aiohttp_jinja2.template("nodes/page.html")
    async def node_page(self, request):
        """
        A single page for a given node.
        """
        context = self.controller.base_context()
        context['node'] = self._get_node(request.match_info['name'])
        return context

    # -- JSON Responses

    async def node_log(self, request):
        """
        Based on the node in the request and of the the query
        parameters, check to see if we have any logging information
        to return.
        """
        node = self._get_node(request.match_info['name'])
        querydict = request.query

        position = 0
        if 'position' in querydict:
            try:
                position = int(querydict['position'])
            except Exception as e:
                raise web.HTTPBadRequest()
        new_lineno, nodelog = self.controller.node_log(node, position)

        return web.json_response(
            {'content' : nodelog, 'position' : new_lineno}
        )


    def register_routes(self, app):
        """
        Register the proper node endpoints for the root controller
        web service.
        """
        app.add_routes([
            web.get('/nodes', self.nodes),
            web.get(r'/nodes/{name:[^/]+}', self.node_page),
            web.get(r'/nodes/{name:[^/]+}/log', self.node_log),
        ])

    # -- Private Methods

    def _get_node(self, name):
        """
        :return: ``NodeRegister`` instance if found. Raise 404 if not
        """
        node = self.controller.get_node(name)
        if node is None:
            raise web.HTTPNotFound(text=f'Unknown none: {name}')
        return node
