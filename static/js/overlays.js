/**
 * Created by JohnsonCharles on 22-03-2016.
 */

function showOverlay(container, msg) {
    if (container == undefined) {
        $.blockUI({
            message: (msg == undefined)?'<h4>Please wait...</h4>':'<h4>' + msg + '</h4>',
            css: {
                border: 'none',
                padding: '15px',
                backgroundColor: '#000',
                '-webkit-border-radius': '10px',
                '-moz-border-radius': '10px',
                opacity: .75,
                color: '#fff'
            }
        });
    } else {
        $(container).block({
            message: (msg == undefined)?'<h4>Please wait...</h4>':'<h4>' + msg + '</h4>',
            css: {
                border: 'none',
                padding: '15px',
                backgroundColor: '#000',
                '-webkit-border-radius': '10px',
                '-moz-border-radius': '10px',
                opacity: .75,
                color: '#fff'
            }
        });
    }

}

function hideOverlay(container) {
    (container==undefined)?$.unblockUI():$(container).unblock();
}