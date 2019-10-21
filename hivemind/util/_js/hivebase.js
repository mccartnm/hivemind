
// -- Hivemind Namespace
'use strict';
var Hivemind = {};

(function() {

/*
    Querying Facilities. TODO: Docs and probably move towards a much
    better system for all this cruft
*/

function status(response)
{
    if (response.status >= 200 && response.status < 300)
    {
        return Promise.resolve(response);
    }
    else
    {
        return Promise.reject(new Error(response.statusText));
    }
}

function get_json(response)
{
    return response.json();
}

function hive_fetch_json(endpoint, options, on_success, on_failure)
{
    options = options || {};

    if (!on_success)
    {
        on_success = function(response) {}; // Do nothing
    }

    if (!on_failure)
    {
        on_failure = function (error) {
            console.log('Request failed', error);
        }
    }

    return fetch(endpoint, options)
        .then(status)
        .then(get_json)
        .then(on_success)
        .catch(on_failure);
}
Hivemind.fetch_json = hive_fetch_json;

})();
