/*
    Basic script tooling for our node index
*/

(function() {

'use strict';
Hivemind.nodes = {}

function get_cards(element_id)
{
    var element = $(element_id);
    Hivemind.fetch_json(
        '/api/render/nodecards/nodes/node',
        {},
        (data) => {
            data.content.forEach((card) => {
                element.append(card);
            });
        }
    );
}

Hivemind.nodes.get_cards = get_cards;

})();