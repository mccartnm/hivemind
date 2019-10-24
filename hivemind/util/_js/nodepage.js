/*
    Basic script tooling for our node index
*/

(function() {

'use strict';
Hivemind.nodes = {};

/*
    Start streaming the log from our hive for a given node id
*/
function start_log(node_name, element_id, options)
{
    options = options || {};
    var position = -100;
    var element = $(element_id);
    var log_func = (() => {
        Hivemind.fetch_json(
            /* endpoint */
            '/nodes/' + node_name + '/log',

            /* options */
            {
                'params' : {
                    'position' : position
                }
            },

            /* on_success */
            (data) => {

                // Auto scroll if we're at the bottom
                var autoScroll = false;
                var e = element[0];
                var offset = (e.scrollHeight - e.offsetHeight);
                if (e.scrollTop <= (offset + 1) && e.scrollTop >= (offset - 1))
                {
                    autoScroll = true;
                }
                else
                {
                    console.log(e.scrollTop, e.scrollHeight, e.offsetHeight, e.scrollHeight - e.offsetHeight);
                }

                data.content.forEach((line) => element.append(line + '<br/>'))
                position = data.position;

                if (autoScroll)
                {
                    setTimeout(() => {
                        console.log('running...');
                        console.log(e.scrollTop, e.scrollHeight, e.offsetHeight, e.scrollHeight - e.offsetHeight);
                        e.scrollTop = (e.scrollHeight - e.offsetHeight);
                    }, 10);
                }
            });
    });
    setTimeout(log_func, 10);
    var interval = setInterval(log_func, 3000);
};
Hivemind.nodes.start_log = start_log;

})();