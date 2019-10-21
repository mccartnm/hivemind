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
from .abstract import _Renderable

class Card(_Renderable):
    """
    Cards are a useful item for displaying quick access, highly
    readable information pannels
    """
    name = 'cards'

    template = r"""
    <div class="card blue-grey darken-1">
        {% if item.image %}
        <div class="card-image">
            <img src="{{ item.image }}">
            <span class="card-title">{{ item.title }}</span>
        </div>
        {% endif %}
        <div class="card-content">
            {% if not item.image %}<span class="card-title">{{ item.title }}</span>{% endif %}
            <p>{{ item.description }}</p>
        </div>
        <div class="card-action">
            <a href="{{ item.index_url }}">{{ item.index_url_title }}</a>
        </div>
    </div>
    """


class NodeCard(_Renderable):
    """
    Card that hosts information on a single node
    """
    name = 'nodecards'

    template = r"""
    <div class="node">
        <div class="node-title">{{ item.name }}</div>
        {% for info in item.infos %}
            <div class="node-chip {{ info.status|lower }}">
                {{ info.status }}
            </div>
        {% endfor %}
        </div>
    </div>
    """
