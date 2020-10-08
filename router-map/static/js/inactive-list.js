import $ from 'jquery';
import {handleConnectionFail, connection_timeout} from './connection-fail'

function displayInactiveList(visualisation_type, id) {
    $.ajax({
        url: '/' + visualisation_type + '/' + id + '/inactive_connections',
        type: "get",
        dataType: "html",
        cache: false,
        timeout: connection_timeout
    }).done(function (response) {
            let list = $('#inactive_list');
            list.empty();
            $('#card-right').html(response);
            $('#close_right_card_btn').click(function () {
                $('#card-right').fadeOut();
            });
            $('#card-right').fadeIn();
        })
        .fail(handleConnectionFail);
}


export {displayInactiveList}
