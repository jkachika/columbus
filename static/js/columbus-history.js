/**
 * Created by JohnsonCharles on 07-06-2016.
 */
var map;
var fusionLayers = [];
var mapInitialized;
var _lastHistory;
var _hlistWrapper;
//var $searchInput;
var rtimestamp;
var $eol;
var _isAbort;
var _lastAjax;
var _lastTimer;
var $historyDetails;
var $noHistory;
var axisOptions;
var ftcOptions;
var yaxes = 1;
var CLIENT_ID = '492266571222-lk6vohmrf2fkkvkmjfi5583qj30ijjkc.apps.googleusercontent.com';

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
function sameOrigin(url) {
    // test that a given url is a same-origin URL
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}


$(document).ready(function () {

    //needed for ajax post requests to be successful
    var csrftoken = $.cookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    //_hlistWrapper = $('#history-listwrapper');
    //$searchInput = $('#search-input');
    $eol = $('#events-ol');
    $historyDetails = $('#history-details');
    /*$noHistory = $('#no-history');
     resizeWrappers();
     $(window).resize(function () {
     resizeWrappers();
     });*/
    $('body').on('click', function (e) {
        $('a[data-toggle=popover]').each(function () {
            // hide any open popovers when the anywhere else in the body is clicked
            if (!$(this).is(e.target) &&
                $(this).has(e.target).length === 0 &&
                $('.popover').has(e.target).length === 0) {
                $(this).popover('hide');
            }
        });
        $('a[data-toggle="popover"]').popover({
            container: "body",
            html: "true",
            content: function () {
                $('#popover-desc').html($(this).data('desc'));
                var type = $(this).data('type');
                if ($(this).data('componentid').trim() != '' &&
                    (type == 'csv' || type == 'ftc' || type == 'mftc')) {
                    $('#popover-form').removeClass('hidden');
                    var vop = "viewOutput('" + $(this).data('type') + "', '" + $(this).data('fsid') + "', '" +
                        $(this).data('flowid') + "', '" + $(this).data('component') + "');";
                    $('#view-output').attr('onclick', vop);
                    var ftkey = $(this).data('ftkey');
                    if ((type != 'ftc' && type != 'mftc') || ftkey == undefined || ftkey == '')
                        $('#visualize').addClass('hidden');
                    else {
                        $('#visualize').removeClass('hidden')
                            .attr('onclick', 'visualizeFTC("' + ftkey + '");');
                    }
                } else {
                    $('#popover-form').addClass('hidden');
                }
                return $('#popover-content').html();
            }
        }).on('shown.bs.popover', function () {
            $('a[data-date]').removeClass('selected');
            $(this).addClass('selected');
        }).on('click', function (e) {
            e.stopPropagation();
            $(this).popover('show');
        });
    });

    /*var hid = $('#open-history').data('historyid');
     if (hid != "0")
     $("#hid-" + hid).click();

     $('div.listitem').each(function () {
     if ($(this).data('status') != "Finished" && $(this).data('status') != "Failed")
     updateHistory($(this).data("historyid"));
     });*/

    $('#addY').click(function () {
        if (yaxes < 4) {
            yaxes++;
            $('#y' + yaxes).selectpicker('show');
        }
        return false;
    });

    $('#removeY').click(function () {
        if (yaxes > 1) {
            $('#y' + yaxes).selectpicker('hide');
            yaxes--;
        }
        return false;
    });

    $('#chart-collection').on('change', function () {
        var ftcindex = $(this).val();
        var $chartLink = $('#history-chart');
        var flowid = $chartLink.attr('data-flowid');
        var fsid = $chartLink.attr('data-fsid');
        $.ajax({
            type: "GET",
            url: "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=columns&ftcindex=" + ftcindex,
            dataType: 'json',
            success: function (data) {
                axisOptions = '';
                $.each(data.result, function (index, column) {
                    axisOptions += '<option>' + column + '</option>';
                });
                $('#xaxis').html(axisOptions).selectpicker('refresh');
                for (var i = 1; i <= 4; i++)
                    $('#y' + i).html(axisOptions).selectpicker('refresh');
            }
        });
    });

    showFlow($('#history-id').val());
});

/*function resizeWrappers() {
 _hlistWrapper.nanoScroller({destroy: true}); //for destroy nano
 _hlistWrapper.nanoScroller();
 }*/

/*function showInstances() {
 var searchText = $searchInput.val().trim();
 var search = (searchText.length > 0) ? true : false;
 var found = false;
 $('div.listitem').each(function () {
 if (searchText.length > 0) {
 if ($(this).text().toLowerCase().indexOf(searchText.toLowerCase()) != -1) {
 $(this).show();
 found = true;
 } else {
 $(this).hide();
 }
 } else {
 $(this).show();
 }
 });

 if (search && !found)
 $('#not-found').show();
 else
 $('#not-found').hide();

 }*/

function showFlow(hid) {
    /*if ($(listitem).data('executing')) {
     $(listitem).css('background-color', '#F9A825');
     $(listitem).css('color', '#fff');
     $("#dhid-" + $(_lastHistory).data("historyid")).collapse('toggle');
     return;
     }

     $noHistory.addClass('hidden');*/
    $historyDetails.removeClass('hidden');

    /*if (_lastHistory != undefined) {
     $(_lastHistory).css('background-color', '');
     $(_lastHistory).css('color', '');
     $(_lastHistory).removeData('executing');
     }
     _lastHistory = listitem;
     $(listitem).css('background-color', '#F9A825');
     $(listitem).css('color', '#fff');
     $(listitem).data('executing', true);
     resizeWrappers();
     $('#history-name').text($(listitem).data('flowname'));*/
    if (_lastAjax != undefined) {
        _isAbort = true;
        _lastAjax.abort();
    }
    if (_lastTimer != undefined)
        window.clearTimeout(_lastTimer);
    $eol.html('');
    var e = $.Event('keyup');
    e.which = 37; // left key press to reset the timeline back to the first event before making a call for re-rendering.
    $(document).trigger(e);
    $('head').find('#dynamic-style').html('');
    peekstatus($eol, undefined, 0, 0, hid);
    resetOutput();
}


/*function findNewHistory(hid) {
 $.ajax({
 type: "GET",
 url: "/hasync/?what=find&id=" + hid,
 dataType: 'json',
 success: function (response) {
 if (response.data == "error") {
 showErrorGrowl("Something went wrong!", "Failed to find new workflow instances, please try again by refreshing the page.");
 return;
 }
 if (response.data == "none")
 return;

 var history = response.data;
 var clazz = "listitem";
 if (history.status == "Queued")
 clazz = "listitem pending";
 else if (history.status == "Started")
 clazz = "listitem started";
 else if (history.status == "In Progress")
 clazz = "listitem running";
 else if (history.status == "Failed")
 clazz = "listitem failed";
 else
 clazz = "listitem finished";

 var html = '<div id="hid-' + history.id + '"' +
 'data-historyid="' + history.id + '"' +
 'data-start="' + history.start + '"' +
 'data-finish="' + history.end + '"' +
 'data-duration="' + history.duration + '"' +
 'data-flowname="' + history.name + '"' +
 'data-source="' + history.source + '"' +
 'data-details="' + history.details + '"' +
 'data-status="' + history.status + '"' +
 'class="' + clazz + '"' +
 'onclick="showFlow(this);">';

 if (history.status == "Failed" || history.status == "Finished") {
 html = html + '<a href="#" class="close" aria-label="close"' +
 'onclick="deleteHistory(event, this, ' + history.id + ');">&times;</a>';
 }

 html = html + '<span id="hdt-' + history.id + '"' +
 'style="font-size:14px; font-weight: 400">' + history.details + '</span><br>' +
 '<span style="font-size: 12px; font-weight: 100">' + history.name + '</span>' +
 '<div style="font-size: 13px; font-weight: 300; margin-top: 10px;"' +
 'id="dhid-' + history.id + '" class="collapse">' +
 '<table border="0px"><tr><td colspan="2">' +
 '<p>Started on<br/>' + history.start + '</p></td></tr><tr><td colspan="2">' +
 '<p>Ended on<br/><span id="hend-' + history.id + '"></span></p></td></tr><tr><td>' +
 '<p>Duration<br/><span id="hdur-' + history.id + '"></span></p></td><td>' +
 '<p>Source<br/>' + history.source + '</p></td></tr><tr><td colspan="2">' +
 '<p>Status<br/><span id="hst-' + history.id + '">' + history.status + '</span></p></td></tr></table>' +
 '</div></div>';

 $('#history-list').prepend(html);
 resizeWrappers();
 updateHistory(history.id);
 },
 error: function () {
 //ignore
 }
 });
 }


 function updateHistory(hid) {
 $.ajax({
 type: "GET",
 url: "/hasync/?what=status&id=" + hid,
 dataType: 'json',
 success: function (response) {
 var history = response.data;
 var $hid = $('#hid-' + history.id);
 $hid.data('status', history.status);
 $hid.find('#hdt-' + history.id).text(history.details);
 $hid.find('#hst-' + history.id).text(history.status);
 $hid.find('#hend-' + history.id).text(history.end);
 $hid.find('#hdur-' + history.id).text(history.duration);
 $hid.css('background-color', '');
 $hid.css('color', '');
 $hid.removeAttr('class');
 if (history.status == 'Queued') {
 $hid.addClass('listitem pending');
 window.setTimeout(function () {
 updateHistory(history.id);
 }, 2000);
 } else if (history.status == 'Started') {
 $hid.addClass('listitem started');
 window.setTimeout(function () {
 updateHistory(history.id);
 }, 2000);
 } else if (history.status == 'In Progress') {
 $hid.addClass('listitem running');
 window.setTimeout(function () {
 updateHistory(history.id);
 }, 5000);
 } else if (history.status == 'Failed') {
 $hid.addClass('listitem failed');
 if (!$hid.find('a.close').length) {
 $hid.prepend('<a href="#" class="close" aria-label="close" onclick="deleteHistory(event, this, ' +
 history.id + ');">&times;</a>');
 }
 window.setTimeout(function () {
 findNewHistory(history.id);
 }, 5000);
 } else {
 $hid.addClass('listitem finished');
 if (!$hid.find('a.close').length) {
 $hid.prepend('<a href="#" class="close" aria-label="close" onclick="deleteHistory(event, this, ' +
 history.id + ');">&times;</a>');
 }
 window.setTimeout(function () {
 findNewHistory(history.id);
 }, 5000);
 }
 }
 });
 }*/

//prevts - previous timestamp
function peekstatus($eol, prevts, count, fsid, flowid) {
    _lastAjax = $.ajax({
        type: "GET",
        url: "/peekflow/?flowid=" + flowid + "&fsid=" + fsid,
        dataType: 'json',
        success: function (data) {
            if (data.status == 'success' || data.status == 'finished' || data.status == 'failure') {
                $.each(data.message, function (index, message) {
                    rtimestamp = message.timestamp.split('.');
                    var timestamp = rtimestamp[0];
                    var milliseconds = parseInt(rtimestamp[1]);
                    rtimestamp = timestamp + '.' + milliseconds;
                    if (count != 0) {
                        var prevtime = prevts.split(".");
                        var prevtimestamp = prevtime[0];
                        var prevms = parseInt(prevtime[1]);
                        if (prevtimestamp == timestamp && prevms <= milliseconds) {
                            milliseconds++;
                            rtimestamp = timestamp + '.' + milliseconds;
                        }
                    }
                    fsid = message.id
                    var html = '<li>' +
                        '<a href="#" data-date="' + rtimestamp + '" data-toggle="popover" ' +
                        'data-trigger="manual" title="' + message.element + '" ' +
                        'data-placement="bottom" data-component="' + message.element + '"' +
                        'data-html="true"' +
                        'data-flowid="' + message.flowid + '"' +
                        'data-fsid="' + message.id + '"' +
                        'data-desc="' + encodeURI(String(message.description)) + '"' +
                        'data-componentid="' + message.ref + '"' +
                        'data-type="' + message.type + '"' +
                        'data-ftkey="' + message.ftkey + '"' +
                        'data-result="' + message.result + '">' +
                        '<label class="timeline-title">' + message.title + '</label><br/>' +
                        '<label class="timeline-subtitle">' + timestamp + '</label>' +
                        '</a>' +
                        '</li>';
                    $eol.append(html);
                    count = 1;
                    prevts = rtimestamp;
                });

                if (data.status == 'failure') {
                    var dynamicStyle = $("head").find('#dynamic-style');
                    dynamicStyle.html(getDynamicStyle('#B22222', 'fail'));
                }
                if (data.status == 'finished') {
                    var dynamicStyle = $("head").find('#dynamic-style');
                    dynamicStyle.html(getDynamicStyle('#228B22', 'done'));
                }
                renderTimeline();
                $('a[data-toggle="popover"]').popover({
                    container: "body",
                    html: "true",
                    content: function () {
                        $('#popover-desc').html(decodeURI($(this).data('desc')));
                        var type = $(this).data('type');
                        if ($(this).data('componentid').trim() != '' &&
                            (type == 'csv' || type == 'ftc' || type == 'mftc')) {
                            $('#popover-form').removeClass('hidden');
                            var vop = "viewOutput('" + $(this).data('type') + "', '" + $(this).data('fsid') + "', '" +
                                $(this).data('flowid') + "', '" + $(this).data('component') + "');";
                            $('#view-output').attr('onclick', vop);
                            var ftkey = $(this).data('ftkey');
                            if ((type != 'ftc' && type != 'mftc') || ftkey == undefined || ftkey == '')
                                $('#visualize').addClass('hidden');
                            else {
                                $('#visualize').removeClass('hidden')
                                    .attr('onclick', 'visualizeFTC("' + ftkey + '");');
                            }
                        } else {
                            $('#popover-form').addClass('hidden');
                        }
                        return $('#popover-content').html();
                    }
                }).on('shown.bs.popover', function () {
                    $('a[data-date]').removeClass('selected');
                    $(this).addClass('selected');
                }).on('click', function (e) {
                    e.stopPropagation();
                    $(this).popover('show');
                });
                if (data.status == 'success')
                    _lastTimer = window.setTimeout(function () {
                        peekstatus($eol, rtimestamp, 1, fsid, flowid);
                    }, 1000);
                if (data.status == 'wait')
                    _lastTimer = window.setTimeout(function () {
                        peekstatus($eol, rtimestamp, 1, fsid, flowid);
                    }, 10000);
            } else if (data.status == 'error') {
                showErrorGrowl("Something went wrong!", data.message);
            }
        },
        error: function () {
            if (!_isAbort)
                showErrorGrowl('Something went wrong!',
                    "Try refreshing the page and if the issue persists please seek support");
            _isAbort = false;
        }
    });
}

function resetOutput() {
    if (typeof $ !== "undefined" && $.fn.dataTable) {
        var all_settings = $($.fn.dataTable.tables()).DataTable().settings();
        for (var i = 0, settings; (settings = all_settings[i]); ++i) {
            if (settings.jqXHR)
                settings.jqXHR.abort();
        }
    }
    $('#table-div').html('').removeClass('nano-content').addClass('placeholder');
    $('#table-name').addClass('hidden');
    $('#history-chart').addClass('hidden');
    $('#flow-details').removeClass('hidden');
    $('#ftc-map').addClass('hidden');
    $('#ftc-details').addClass('hidden');
    $('#ftc-stats-div').html('');
    $('#ftc-table-div').html('');
    $('#searchPlace').addClass('hidden');

    $('div.popover').remove();
}

function viewCollectionOutput(flowid, index, fsid) {
    var $tableDiv = $('#ftc-table-div');
    var $flowDetails = $('#ftc-table-wrapper');
    $tableDiv.html('<table id="ftc-table" ' +
        'style="margin:0px!important;"' +
        'class="table table-striped table-condensed">' +
        '<thead>' +
        '<tr id="ftc-table-header">' +
        '</tr>' +
        '</thead>' +
        '</table>').removeClass('placeholder').addClass('nano-content');
    $flowDetails.nanoScroller({destroy: true});
    showOverlay();
    $.ajax({
        type: "GET",
        url: "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=columns&ftcindex=" + index,
        dataType: 'json',
        success: function (data) {
            if (data.result.length == 0) {
                $tableDiv.removeClass('nano-content').addClass('placeholder').html('').attr('data-placeholder', 'No data available');
            } else {
                var $tr = $('#ftc-table-header');
                $tr.html('');
                $.each(data.result, function (index, column) {
                    $tr.append('<th>' + column + '</th>');
                });
                var count = data.result.length;
                var totalHeight = Number($tableDiv.css('height').replace('px', ''));
                var rowHeight = Number($('#ftc-table-header').css('height').replace('px', ''));
                var pagingHeight = 35; //paginating footer
                var pageLength = Math.floor((totalHeight - rowHeight - pagingHeight) / rowHeight);
                $('#ftc-table').DataTable({
                    "processing": true,
                    "serverSide": true,
                    "lengthChange": false,
                    "bFilter": false,
                    "pageLength": pageLength,
                    "scrollX": true,
                    "bScrollAutoCss": false,
                    "ajax": {
                        "url": "/peekdata/?ftcindex=" + index + "&flowid=" + flowid + "&fsid=" + fsid + "&what=data&columns=" + count,
                        "type": "POST"
                    }
                });
                $('div.dataTables_scrollBody').css('overflow', 'hidden').hScroll();
            }
            $flowDetails.nanoScroller();
            hideOverlay();
        },
        error: function () {
            $('#ftc-table-div').addClass('placeholder').html('').attr('data-placeholder', 'Something went wrong!');
            hideOverlay();
        }
    });
}

function viewCollection(fsid, flowid, cname) {
    var $statsDiv = $('#ftc-stats-div');
    var $ftcDetails = $('#ftc-details');
    $ftcDetails.removeClass('hidden');
    $('#ftc-table-div').html('').removeClass('nano-content').addClass('placeholder');
    showOverlay();
    $.ajax({
        type: "GET",
        url: "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=ftc",
        dataType: 'json',
        success: function (response) {
            $('#table-name').html(cname).removeClass('hidden');
            $('#history-chart').attr('data-name', cname).attr('data-flowid', flowid).attr('data-fsid', fsid)
                .attr('data-type', 'ftc').removeClass('hidden');
            $statsDiv.html('');
            var stathtml = [];
            ftcOptions = '';
            if (response.result.length > 0) {
                $(response.result).each(function (index, ftc) {
                    ftcOptions += '<option value="' + index + '">' + ftc["id"] + '</option>';
                    var stats = false;
                    if (ftc["statistics"] != undefined && ftc["statistics"] != "none")
                        stats = true;

                    var html = '<div class="panel-group" style="margin-top:10px; margin-bottom:10px;">' +
                        '<div class="panel panel-default">' +
                        '<div class="panel-heading">' +
                        '<h4 class="panel-title">' +
                        '<a data-toggle="collapse" href="#collapse' + index + '">' + ftc["id"] + '</a>' +
                        '</h4>' +
                        '</div>' +
                        '<div id="collapse' + index + '" class="panel-collapse collapse">' +
                        '<div class="panel-body">';
                    if (stats) {
                        var sortedStats = [];
                        for (var property in ftc["statistics"]) {
                            if (ftc["statistics"].hasOwnProperty(property)) {
                                sortedStats.push(property);
                            }
                        }
                        sortedStats = sortedStats.sort();
                        $(sortedStats).each(function (index, property) {
                            html = html + "<p><label>" + property + "</label><br/>" +
                                ftc['statistics'][property] + "</p>";
                        });
                    } else {
                        html = html + '<p>No statistics found</p>';
                    }
                    html = html + '</div>' +
                        '<div class="panel-footer"><a class="btn btn-info" ' +
                        'onclick="viewCollectionOutput(' + flowid + ', ' + index + ', ' + fsid + ');">' +
                        'Show Output</a>&nbsp;&nbsp;<a class="btn btn-warning" ' +
                        'href="/download/?flowid=' + flowid + '&fsid=' + fsid + '&index=' + index + '">' +
                        'Download</a>' +
                        '</div></div></div></div>';
                    stathtml.push(html);
                });
                $statsDiv.append("<div class='nano-content' style='padding-left:10px; padding-right: 10px; right:-17px;'>" +
                    stathtml.join('') + "</div>");
            }
            $statsDiv.nanoScroller();
            hideOverlay();
        },
        error: function (xhr, ajaxOptions, thrownError) {
            console.log("xhr status - " + xhr.status);
            console.log("error - " + thrownError);
            showErrorGrowl("Something went wrong!", "If the issue persists please seek support");
            hideOverlay();
        }
    });
}

function viewOutput(type, fsid, flowid, cname) {
    $('div.popover').remove()
    $('#searchPlace').addClass('hidden');
    $('#ftc-map').addClass('hidden');
    var $tableDiv = $('#table-div');
    var $flowDetails = $('#flow-details');
    if (type == 'ftc' || type == 'mftc') {
        $flowDetails.addClass('hidden');
        viewCollection(fsid, flowid, cname);
        return;
    } else {
        $flowDetails.removeClass('hidden');
        $('#ftc-details').addClass('hidden');
    }
    $tableDiv.html('<table id="' + type + '-table" ' +
        'style="margin:0px!important;"' +
        'class="table table-striped table-condensed">' +
        '<thead>' +
        '<tr id="' + type + '-table-header">' +
        '</tr>' +
        '</thead>' +
        '</table>').removeClass('placeholder').addClass('nano-content');
    $flowDetails.nanoScroller({destroy: true});
    showOverlay();
    $.ajax({
        type: "GET",
        url: "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=columns",
        dataType: 'json',
        success: function (data) {
            $('#table-name').html(cname).removeClass('hidden');
            $('#history-chart').attr('data-name', cname).attr('data-flowid', flowid).attr('data-fsid', fsid)
                .attr('data-type', 'csv').removeClass('hidden');
            if (data.result.length == 0) {
                $tableDiv.removeClass('nano-content').addClass('placeholder').html('').attr('data-placeholder', 'No data available');
            } else {
                var $tr = $('#' + type + '-table-header');
                $tr.html('');
                axisOptions = '';
                $.each(data.result, function (index, column) {
                    $tr.append('<th>' + column + '</th>');
                    axisOptions += '<option>' + column + '</option>';
                });
                var count = data.result.length;
                var totalHeight = Number($tableDiv.css('height').replace('px', ''));
                var rowHeight = Number($tr.css('height').replace('px', ''));
                var pagingHeight = 35; //paginating footer
                var pageLength = Math.floor((totalHeight - rowHeight - pagingHeight) / rowHeight);
                $('#' + type + '-table').DataTable({
                    "processing": true,
                    "serverSide": true,
                    "lengthChange": false,
                    "bFilter": false,
                    "pageLength": pageLength,
                    "scrollX": true,
                    "bScrollAutoCss": false,
                    "ajax": {
                        "url": "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=data&columns=" + count,
                        "type": "POST"
                    }
                });
                $('div.dataTables_scrollBody').css('overflow', 'hidden').hScroll();
            }
            $flowDetails.nanoScroller();
            hideOverlay();
        },
        error: function () {
            $('#table-div').addClass('placeholder').html('').attr('data-placeholder', 'Something went wrong!');
            hideOverlay();
        }
    });
}

function showErrorGrowl(title, message) {
    $.growl.error({
        title: title,
        message: message,
        location: 'tc',
        delayOnHover: true,
        duration: 5000
    });
}

function getDynamicStyle(color, status) {
    return '.cd-horizontal-timeline .events a.selected::after,' +
        ' .no-touch .cd-horizontal-timeline .events a:hover::after,' +
        ' .cd-horizontal-timeline .events a.older-event:hover::after{' +
        'background-color: ' + color + ';' +
        'border-color: ' + color + '}' +
        '.cd-horizontal-timeline .events a.older-event::after{' +
        'border-color: ' + color + '}' +
        '.cd-horizontal-timeline .filling-line{' +
        'background-color: ' + color + '}' +
        '.no-touch .cd-timeline-navigation a:hover {' +
        'border-color: ' + color + ';}' +
        '.cd-timeline-navigation a::after{' +
        'background: url(../static/images/cd-arrow-' + status + '.svg) no-repeat 0 0;}'
}

// called by the google maps api
function initMap() {
    //Enabling new cartography and themes
    google.maps.visualRefresh = true;
    var mapOptions = {
        center: new google.maps.LatLng(38, -100),
        zoom: 5,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        panControl: false,
        zoomControl: true,
        scaleControl: true,
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_LEFT
        },
        zoomControlOptions: {
            style: google.maps.ZoomControlStyle.SMALL,
            position: google.maps.ControlPosition.RIGHT_BOTTOM
        }
    };
    //Getting map DOM element
    var mapElement = $('#ftc-map')[0];
    map = new google.maps.Map(mapElement, mapOptions);
    var infowindow = new google.maps.InfoWindow();
    var marker = new google.maps.Marker({
        map: map
    });
    marker.addListener('click', function () {
        infowindow.open(map, marker);
    });
    // Create the search box and link it to the UI element.
    var searchPlace = $('#searchPlace')[0];
    var autocomplete = new google.maps.places.Autocomplete(searchPlace);
    autocomplete.bindTo('bounds', map);
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(searchPlace);

    autocomplete.addListener('place_changed', function () {
        infowindow.close();
        var place = autocomplete.getPlace();
        if (!place.geometry) {
            return;
        }
        if (place.geometry.viewport) {
            map.fitBounds(place.geometry.viewport);
        } else {
            map.setCenter(place.geometry.location);
            map.setZoom(8);
        }
    });
}

function windowControl(e, infoWindow, map) {
    infoWindow.setOptions({
        content: e.infoWindowHtml,
        position: e.latLng,
        pixelOffset: e.pixelOffset
    });
    infoWindow.open(map);
}

var marker_icons = ['small_red', 'small_yellow', 'small_green', 'small_purple', 'small_blue'];
var poly_colors = ['EF9A9A', 'FFEB3B', '1DE9B6', 'B39DDB', '90CAF9'];

function showLayer(layer) {
    var layerIndex = $(layer).data('layer');
    var ftkey = $(layer).data('ftkey');
    if ($(layer).attr('selected')) {
        $(layer).attr('selected', false);
        $(layer).find('img').css('display', 'none');
        if (fusionLayers[layerIndex] != undefined && fusionLayers[layerIndex] != null) {
            if (layerIndex == 0)
                fusionLayers[layerIndex].setMap(null);
            else {
                map.overlayMapTypes.clear();
                var selectedLayers = $(layer).parent().find('div.layer[selected=selected]');
                $(selectedLayers).each(function (index, selectedLayer) {
                    var selectedIndex = $(selectedLayer).data('layer');
                    map.overlayMapTypes.push(fusionLayers[selectedIndex]);
                });
            }
        }
    } else {
        $(layer).attr('selected', true);
        $(layer).find('img').css('display', '');
        if (fusionLayers[layerIndex] != undefined && fusionLayers[layerIndex] != null) {
            if (layerIndex == 0)
                fusionLayers[layerIndex].setMap(map);
            else {
                map.overlayMapTypes.push(fusionLayers[layerIndex]);
            }
        } else {
            if (layerIndex > 0) {
                var ftc = ee.FeatureCollection('ft:' + ftkey);
                var mapId = ftc.getMap({'color': poly_colors[layerIndex]});
                var overlay = new ee.MapLayerOverlay('https://earthengine.googleapis.com/map', mapId.mapid,
                    mapId.token, {});
                map.overlayMapTypes.push(overlay);
                fusionLayers[layerIndex] = overlay;
            }
        }
    }
}

var onImmediateFailed = function () {
    $('.g-sign-in').removeClass('hidden');
    $('.g-sign-in .button').click(function () {
        ee.data.authenticateViaPopup(function () {
            // If the login succeeds, hide the login button and run the analysis.
            $('.g-sign-in').addClass('hidden');
            initializeGEE();
        });
    });
};

var initializeGEE = function () {
    ee.initialize();
};

function visualizeFTC(ftkey) {
    $('div.popover').remove();
    $('#flow-details').addClass('hidden');
    $('#ftc-details').addClass('hidden');
    $('#ftc-map').removeClass('hidden');
    $('#searchPlace').removeClass('hidden');

    $(fusionLayers).each(function (index, fusionLayer) {
        if (index == 0 && fusionLayer != undefined && fusionLayer != null)
            fusionLayer.setMap(null);
    });

    if (!mapInitialized) {
        initMap();
        mapInitialized = true;
        // Attempt to authenticate for Earth Engine using existing credentials.
        ee.data.authenticate(CLIENT_ID, initializeGEE, null, null, onImmediateFailed);
    }
    //map.controls[google.maps.ControlPosition.RIGHT_TOP].push("<input type='text' value='hello'>");
    var ftkeys = ftkey.split(',', 5); //supporting only 5 layers
    map.setZoom(5);
    fusionLayers = new Array(ftkeys.length);
    var layerHTMLArray = [];
    map.controls[google.maps.ControlPosition.TOP_RIGHT].clear();
    map.overlayMapTypes.clear();
    $(ftkeys).each(function (index, ftkey) {
        var layerHTML = '<div class="layer" data-ftkey="' + ftkey + '" data-layer="' + index + '" ' +
            'onclick="showLayer(this);" ' + ((index == 0) ? 'selected="selected">' : '>') +
            '<div class="map-control-checkbox">' +
            '<div class="map-control-checkbox-wrapper">' +
            '<img id="layer-checkbox-' + index + '" class="map-control-checkbox-img" ' +
            'src="/static/images/imgs8.png" style=' + ((index != 0) ? '"display: none"' : '""') + '>' +
            '</div>' +
            '</div>' +
            '<span class="name">Layer ' + (index + 1) + '</span>' +
            '</div>';
        layerHTMLArray.push(layerHTML);
    });
    var centerControlDiv = document.createElement('div');
    centerControlDiv.innerHTML = '<div class="gmap-control map-control-list layer-list" style="z-index: 0; position: absolute; right: 10px; top: 0px; bottom: auto;">' +
        '<div class="inner">' +
        '<div class="title">Layers</div>' +
        '<div id="gmaps-layers-list" class="layers-list" style="overflow-y: hidden;">' +
        layerHTMLArray.join('\n') +
        '</div>' +
        '</div>' +
        '</div>';
    centerControlDiv.index = 1;
    map.controls[google.maps.ControlPosition.TOP_RIGHT].push(centerControlDiv);
    //visualizing only the first fusion table
    var fusionLayer = new google.maps.FusionTablesLayer({
        query: {
            select: 'x__geometry__x',
            from: ftkeys[0]
        },
        map: map,
        suppressInfoWindows: true
    });
    var infoWindow = new google.maps.InfoWindow();
    google.maps.event.addListener(fusionLayer, 'click', function (e) {
        windowControl(e, infoWindow, map);
    });
    fusionLayers[0] = fusionLayer;

    /*$(fusionLayers).each(function (index, fusionLayer) {
     fusionLayer.setMap(map);
     });*/
}

/*function deleteHistory(e, anchor, hid) {
 showOverlay();
 e.stopPropagation();
 if (!$(anchor).data("executing")) {
 $(anchor).data("executing", true);
 $.ajax({
 type: "GET",
 url: "/delete/?what=history&id=" + hid,
 dataType: 'json',
 success: function (response) {
 if (response.result != "success") {
 showErrorGrowl("Something went wrong!", "Failed to delete the instance. If the issue persists, please seek support");
 } else {
 //deleting the div in advance to imitate that it did not take time.
 var $hid = $("div#hid-" + hid);
 if ($hid.data('executing')) {
 $noHistory.removeClass('hidden');
 $historyDetails.addClass('hidden');
 }
 $hid.remove();
 if ($('div.listitem').length == 0)
 $('#no-instances').removeClass('hidden');
 resizeWrappers();
 }
 hideOverlay();
 },
 error: function () {
 showErrorGrowl("Something went wrong!", "Failed to delete the instance. " +
 "If the issue persists, please seek support.");
 hideOverlay();
 }
 });
 }
 }*/

function buildChartXAxis() {
    var xaxisVal = $('#xaxis').val();
    if (xaxisVal != undefined && xaxisVal != '') {
        return {
            title: {
                text: xaxisVal
            },
            lineWidth: 1,
            lineColor: '#92A8CD',
            tickWidth: 2,
            tickLength: 6,
            tickColor: '#92A8CD'
        };
    }
}

var axiscolors = ['#FF00FF', '#F88017', '#168EF7', '#006400'];

function buildChartYAxis() {
    var y = [];
    for (var i = 1; i <= yaxes; i++) {
        var yival = $('#y' + i).val();
        if (yival != 'undefined') {
            if (i % 2 == 0) {
                y.push({
                    title: {text: yival, style: {color: axiscolors[y.length]}},
                    opposite: true,
                    lineColor: axiscolors[y.length],
                    lineWidth: 2,
                    tickWidth: 2,
                    tickLength: 6
                });
            } else {
                y.push({
                    title: {text: yival, style: {color: axiscolors[y.length]}},
                    lineWidth: 2,
                    lineColor: axiscolors[y.length],
                    tickWidth: 2,
                    tickLength: 6
                });
            }
        }
    }
    return y;

}

function buildChartSeries(y, chartData) {
    var series = [];
    if (y.length != 0) {
        for (var i = 0; i < y.length; i++) {
            var yval = y[i];
            data = [];
            $(chartData).each(function (index, row) {
                var datum = [];
                datum.push(Number(row[0]));
                datum.push(Number(row[i + 1]));
                data.push(datum);
            });
            series.push({name: yval, color: axiscolors[i], yAxis: i, data: data, lineWidth: 1})
        }
    }
    return series;
}

function __showChart(chartTitle, chartType, xval, yval, series) {

    new Highcharts.Chart({
        chart: {
            renderTo: 'chart-container',
            type: chartType,
            borderColor: '#a1a1a1',
            borderWidth: 1,
            borderRadius: 3,
            zoomType: 'x'
        },
        title: {
            text: chartTitle
        },
        legend: {
            borderWidth: 1,
            borderRadius: 3
        },
        xAxis: xval,
        yAxis: yval,
        series: series,
        tooltip: {
            //xDateFormat: '%a, %Y %b %e - %I:%M:%S %P',
            borderColor: '#808080',
            shared: true,
            valueSuffix: ' units'
        },
        plotOptions: {
            areaspline: {
                fillOpacity: 0.5
            }
        }
    });
}


function displayChart() {
    var $chartLink = $('#history-chart');
    var ftcindex;
    if ($chartLink.attr('data-type') == 'ftc') {
        ftcindex = $('#chart-collection').val();
        if (ftcindex == undefined || ftcindex == '') {
            $('button[data-id=chart-collection]').focus();
            return false;
        }
    }
    if (ftcindex == undefined || ftcindex == '')
        ftcindex = 0;

    var xaxis = $('#xaxis').val();
    if (xaxis == undefined || xaxis == '') {
        $('button[data-id=xaxis]').focus();
        return false;
    }
    var y_axes = [];
    for (var i = 1; i <= yaxes; i++) {
        var yaxis = $('#y' + i).val();
        if (yaxis == undefined || yaxis == '') {
            $('button[data-id=y' + i + ']').focus();
            return false;
        } else {
            y_axes.push(yaxis);
        }
    }
    var fields = xaxis + "," + y_axes.join();
    var chartX = buildChartXAxis();
    var chartY = buildChartYAxis();
    var chartType = $('#chart-type').val();
    var chartTitle = $chartLink.attr('data-name');
    var $showButton = $(this);
    $showButton.attr('disabled', true);
    $('#chart-loading').removeClass('hidden');
    var flowid = $chartLink.attr('data-flowid');
    var fsid = $chartLink.attr('data-fsid');
    $.ajax({
        type: "GET",
        url: "/peekdata/?flowid=" + flowid + "&fsid=" + fsid + "&what=chart&ftcindex=" + ftcindex + "&fields=" + fields,
        dataType: 'json',
        success: function (data) {
            if (data.result.length == 0)
                $('#chart-container').html('<p style="display: table-cell; text-align: center; ' +
                    'vertical-align: middle;">No data found for the chosen criteria</p>');
            else {
                var chartSeries = buildChartSeries(y_axes, data.result);
                __showChart(chartTitle, chartType, chartX, chartY, chartSeries);
                $showButton.removeAttr('disabled');
                $('#chart-loading').addClass('hidden');
            }
        }
    });
}


function buildChart(chartLink) {
    var type = $(chartLink).attr('data-type');
    var name = $(chartLink).attr('data-name');
    $('#chart-window').modal('show');
    $('#chart-modal').text(name);
    $('#chart-container').html('<p style="display: table-cell; text-align: center; ' +
        'vertical-align: middle;">Select axes and click on <b>Show Chart</b> button</p>');
    $('#chart-loading').addClass('hidden');
    yaxes = 1;
    for (var i = 2; i <= 4; i++)
        $('#y' + i).selectpicker('hide');

    if (type == 'csv') {
        $('#chart-collection').selectpicker('hide');
        $('#xaxis').html(axisOptions).selectpicker('refresh');
        for (var i = 1; i <= 4; i++)
            $('#y' + i).html(axisOptions).selectpicker('refresh');
    } else {
        var $chartCollection = $('#chart-collection');
        $chartCollection.selectpicker('show');
        $chartCollection.html(ftcOptions).selectpicker('refresh');
        $('#xaxis').html('').selectpicker('refresh');
        for (var i = 1; i <= 4; i++)
            $('#y' + i).html('').selectpicker('refresh');
    }
    /*var type = $('#chart-type').val();
     if (type == undefined)
     type = 'line';
     var xval = buildChartXAxis();
     var yval = buildChartYAxis();
     var series = buildChartSeries(polygon.geoJSON);
     if (xval != 'undefined' && yval != undefined && yval.length != 0 && series != undefined && series.length != 0) {
     var xtext = xval.title.text;
     showChart(polygon.name + ' Visual Analysis', type, xval, yval, series);
     } else {
     alert('One or more of the chosen options for charting are not supported as of now');
     }*/
}