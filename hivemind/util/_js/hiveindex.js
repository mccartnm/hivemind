(function() {

'use strict';
Hivemind.landing = {};

function get_cards(element_id)
{
    var element = $(element_id);
    Hivemind.fetch_json(
        '/api/render/cards/topics',
        {},
        (data) => {
            data.content.forEach((card) => {
                element.append(card);
            });
        }
    );
}

Hivemind.landing.get_cards = get_cards;

})();