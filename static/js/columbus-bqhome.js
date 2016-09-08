/**
 * Created by JohnsonCharles on 31-05-2016.
 */
var map;
var data = [];
var timer;
var zoom_changed = false;
// needed for handling polygon drawing
var lastPolygon;
var modalClosed;
var lastOverlay;
var drewPolygon;
var layers = [];
var isserviceup; //will be true if service is up and running
var CLIENT_ID = '492266571222-lk6vohmrf2fkkvkmjfi5583qj30ijjkc.apps.googleusercontent.com';
var SCOPES = ['https://www.googleapis.com/auth/drive.readonly'];
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

/*function checkDriveAuth() {
 gapi.auth.authorize({
 'client_id': CLIENT_ID,
 'scope': SCOPES.join(' '),
 'immediate': true
 }, handleDriveAuthResult);
 }

 function handleDriveAuthResult(authResult) {
 if (authResult && !authResult.error) {
 $('#g-sign-in').addClass('hidden');
 $('#floatingDiv').removeClass('hidden');
 loadDriveApi();
 } else {
 // Show auth UI, allowing the user to initiate authorization by
 // clicking authorize button.
 $('#floatingDiv').addClass('hidden');
 $('#g-sign-in').removeClass('hidden');
 $('.g-sign-in').removeClass('hidden');
 $('.g-sign-in .button').click(function () {
 // If the login succeeds, hide the login button and run the analysis.
 //$('.g-sign-in').addClass('hidden');
 gapi.auth.authorize({
 'client_id': CLIENT_ID,
 'scope': SCOPES.join(' '),
 'immediate': false
 }, handleDriveAuthResult);
 });
 }
 }

 function loadDriveApi() {
 gapi.client.load('drive', 'v3', listDriveFiles);
 }*/

/*function listDriveFiles(runType) {
 if (!runType)
 runType = $('input[name=gd-run-type]:checked').val();
 var query = "mimeType = 'application/vnd.google-apps.folder'";
 if (runType == 'for')
 query = "mimeType = 'application/vnd.google-apps.fusiontable' or fileExtension='csv'";
 var request = gapi.client.drive.files.list({
 'pageSize': 1000,
 'fields': "nextPageToken, files(id, name, mimeType, fileExtension)",
 'q': query,
 'orderBy': 'viewedByMeTime desc'
 });
 var $gdIdentifier = $('#gd-identifier');
 $gdIdentifier.html('');
 showOverlay();
 var callback = function (resp) {
 var html = [];
 var files = resp.files;
 if (files && files.length > 0) {
 for (var i = 0; i < files.length; i++) {
 var file = files[i];
 html.push('<option value="' + file.id + '">' + file.name + '</option>');
 }
 $gdIdentifier.append(html.join(''));
 }
 if (resp.nextPageToken) {
 request = gapi.client.drive.files.list({
 'pageSize': 1000,
 'pageToken': resp.nextPageToken,
 'fields': "nextPageToken, files(id, name, mimeType, fileExtension)",
 'q': query,
 'orderBy': 'viewedByMeTime desc'
 });
 request.execute(callback);
 } else {
 hideOverlay();
 initializeScrollOnHover($gdIdentifier);
 }
 };
 request.execute(callback);
 }*/

$(document).ready(function () {
    //need to show the shadow below the header
    $('header').css('position', 'relative');

    //initializing all tooltips
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});

    //to lose focus of the buttons after clicking them
    $(".btn").mouseup(function () {
        $(this).blur();
    });

    //timeout for tooltips
    $('[data-toggle="tooltip"][data-timeout]').on('shown.bs.tooltip', function () {
        var $this = $(this);
        setTimeout(function () {
            $this.tooltip('hide');
        }, $(this).data("timeout"));
    });

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

    //showing overlay for any ajax request
    $(document).ajaxStart(function () {
        showOverlay();
    });

    //hiding overlay after all ajax request complete
    $(document).ajaxStop(function () {
        hideOverlay();
    });

    //check if any errors are presented by the server
    if ($('#error-holder').length != 0) {
        $.growl.error({
            title: 'Something went wrong!',
            message: $('#error-holder').html(),
            location: 'tc',
            delayOnHover: true,
            duration: 0
        });
    }

    //growl css
    $.blockUI.defaults.growlCSS.top = '0px';
    $.blockUI.defaults.growlCSS.opacity = '1';

    var $bqtable = $('#bq-table');
    $.ajax({
        url: "/service/?name=tables",
        type: 'GET',
        dataType: 'json',
        timeout: 60000,
        success: function (response) {
            var html = [];
            $.each(response.result, function (index, group) {
                for (var name in group) {
                    html.push("<optgroup label='" + name + "'>");
                    $.each(group[name], function (index, table) {
                        html.push("<option value='" + name + "." + table + "' title='" + name + "." + table + "'>"
                            + table + "</option>");
                    });
                    html.push("</optgroup>");
                }
            });
            html = html.join('');
            $bqtable.html(html);
            initializeScrollOnHover($bqtable);
        },
        error: function (jqXHR, textStatus) {
            if (textStatus === 'timeout') {
                showErrorGrowl('Server timed out!',
                    'Try refreshing the browser. If the issue persists, please seek support.');
            } else {
                showErrorGrowl('Something went wrong!', 'If the issue persists, please seek support.');
            }
        }
    });

    var $bqfeature = $('#bq-feature-label');
    $bqtable.on('change', function () {
        var table = $(this).val();
        $.ajax({
            url: "/service/?name=features&table=" + table,
            type: 'GET',
            dataType: 'json',
            timeout: 60000,
            success: function (response) {
                var html = [];
                $.each(response.result, function (index, feature) {
                    for (var name in feature) {
                        html.push("<option data-type='" + feature[name] + "' value='" + name + "'>" + name + "</option>");
                    }
                });
                $bqfeature.html(html.join(''));
                initializeScrollOnHover($bqfeature);
            },
            error: function (jqXHR, textStatus) {
                if (textStatus === 'timeout') {
                    showErrorGrowl('Server timed out!',
                        'Try refreshing the browser. If the issue persists, please seek support.');
                } else {
                    showErrorGrowl('Something went wrong!', 'If the issue persists, please seek support.');
                }
            }
        });

        $.ajax({
            url: "/elements/?name=constraint&table=" + table,
            type: 'GET',
            dataType: 'json',
            timeout: 10000,
            success: function (response) {
                var html = [];
                $.each(response.result, function (index, constraint) {
                    html.push("<option value='" + constraint.id + "'>" + constraint.name + "</option>");
                });
                html = html.join('');
                initializeScrollOnHover($('#bq-constraint').html(html));
            },
            error: function (jqXHR, textStatus) {
                if (textStatus === 'timeout') {
                    showErrorGrowl('Server timed out!',
                        'Try refreshing the browser. If the issue persists, please seek support.');
                } else {
                    showErrorGrowl('Something went wrong!', 'If the issue persists, please seek support.');
                }
            }
        });
    });

    $bqfeature.on('change', function () {
        var table = $bqtable.val();
        var feature = $(this).val();
        var option = $(this).find('option:selected');
        $('#bq-feature-type').val(option.data('type'));
        $.ajax({
            url: "/service/?name=first&table=" + table + "&feature=" + feature,
            type: 'GET',
            dataType: 'json',
            timeout: 60000,
            success: function (response) {
                var suggestions = [];
                $.each(response.result.rows, function (index, feature) {
                    suggestions.push(feature[0]["v"]);
                });
                var $bqvalue = $('#bq-feature-value');
                $bqvalue.typeahead('destroy');
                $bqvalue.typeahead({
                    source: suggestions.map(String),
                    showHintOnFocus: true,
                    items: "all"
                });
            },
            error: function (jqXHR, textStatus) {
                if (textStatus === 'timeout') {
                    showErrorGrowl('Server timed out!',
                        'Try refreshing the browser. If the issue persists, please seek support.');
                } else {
                    showErrorGrowl('Something went wrong!', 'If the issue persists, please seek support.');
                }
            }
        });
    });

    //To focus on the input upon showing the modal
    $('#polygon-modal').on('shown.bs.modal', function () {
        $('#polygon-name').focus();
    });

    //to remove the polygon from map if it is not saved
    $('#polygon-modal').on('hidden.bs.modal', function () {
        if (!modalClosed && lastPolygon != undefined)
            lastOverlay.setMap(null);
    });

    //making enter press as save button click
    $("#polygon-name").keyup(function (event) {
        if (event.keyCode == 13) {
            $("#save-polygon").click();
        }
    });

    //saving the polygon
    $('#save-polygon').click(function () {
        var polygonName = $('#polygon-name').val()
        if (polygonName != undefined && polygonName.length != 0 && lastPolygon != undefined) {
            $('#polygon-modal').modal('hide');
            modalClosed = true;
            $.ajax({
                type: "POST",
                url: "/savepolygon",
                data: JSON.stringify({'name': polygonName, 'polygon': lastPolygon}),
                success: function (response) {
                    $('#polygon').append('<option value="' + response.id + '" data-polygon=\'' + response.json + '\'>'
                        + response.name + '</option>');
                    $('#polygon').selectpicker('refresh');
                },
                error: function (jqxhr) {
                    $.growl.error({
                        title: 'Something went wrong!',
                        message: jqxhr.responseText + ". If the issue persists, please seek support.",
                        location: 'tc',
                        delayOnHover: true,
                        duration: 5000
                    });
                    lastOverlay.setMap(null);
                }
            });
        }
    });

    $('#datasource').on('change', function () {
        chooseDatasource($(this).val());
    });
});

function validateForm() {
    var choice = $('input:radio[name=datasource]:checked').val()
    if (choice == 'bigquery') {
        var $bqtable = $('#bq-table');
        var runType = $('input:radio[name=run-type]:checked').val()
        var $bqfeature = $('#bq-feature-label');
        var $bqvalue = $('#bq-feature-value');
        if ($bqtable.val() == undefined || $bqtable.val() == '') {
            $('button[data-id=bq-table]').focus();
            return false;
        }
        if ($bqfeature.val() == undefined || $bqfeature.val() == '') {
            $('button[data-id=bq-feature-label]').focus();
            return false;
        }
        if (runType == 'for' && $bqvalue.val().trim() == '') {
            $bqvalue.val('').focus();
            return false;
        }
    } else if (choice == 'drive') {
        var $gdIdentifier = $('#gd-identifier');
        if ($gdIdentifier.val() == undefined || $gdIdentifier.val() == '') {
            $('button[data-id=gd-identifier]').focus();
            return false;
        }
    }
    var workflow = $('#workflow').val();
    if (workflow == undefined || workflow == '') {
        $('button[data-id=workflow]').focus();
        return false;
    }
    return true;
}

function chooseDatasource(choice) {
    $('#start-flow').removeAttr('disabled');
    if (choice == 'bigquery') {
        $('#bq-details-div').removeClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
    } else if (choice == 'drive') {
        $('#bq-details-div').addClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#gd-details-div').removeClass('hidden');
        //checkDriveAuth();
        var runType = $('input[name="gd-run-type"]:checked').val();
        showOverlay();
        $.ajax({
            type: "GET",
            url: "/data/?source=drive&runtype=" + runType,
            dataType: 'json',
            success: function (response) {
                hideOverlay();
                if (response.what == 'authorize') {
                    console.log(response.result);
                    window.open(response.result, '_self');
                } else if (response.what == 'files') {
                    var files = response.result;
                    var html = [];
                    $(files).each(function (index, file) {
                        html.push('<option value="' + file.id + '">' + file.name + '</option>');
                    });
                    var $gdIdentifier = $('#gd-identifier');
                    $gdIdentifier.html(html.join(''));
                    initializeScrollOnHover($gdIdentifier);
                } else if (response.what == 'error') {
                    showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, please seek support.');
                }
            },
            error: function () {
                hideOverlay();
                showErrorGrowl('Something went wrong!', 'Unable to get the files for google drive. If the issue persists, please seek support')
            }
        });
    } else {
        $('#bq-details-div').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
        $('#combiner-title').removeClass('hidden');
    }
}

function chooseAutorunType(runType) {
    if (runType == "for") {
        $('#bq-feature-op').removeAttr('disabled').selectpicker('refresh');
        $('#bq-feature-value').removeAttr('disabled');
    } else {
        $('#bq-feature-op').attr('disabled', 'true').selectpicker('refresh');
        $('#bq-feature-value').attr('disabled', 'true')
    }
}

function chooseDriveRunType(runType) {
    //listDriveFiles(runType);
    $.ajax({
        type: "GET",
        url: "/data/?source=drive&runtype=" + runType,
        dataType: 'json',
        success: function (response) {
            hideOverlay();
            if (response.what == 'authorize') {
                window.open(response.result);
            } else if (response.what == 'files') {
                var files = response.result;
                var html = [];
                $(files).each(function (index, file) {
                    html.push('<option value="' + file.id + '">' + file.name + '</option>');
                });
                var $gdIdentifier = $('#gd-identifier');
                $gdIdentifier.html(html.join(''));
                initializeScrollOnHover($gdIdentifier);
            } else if (response.what == 'error') {
                showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, please seek support.');
            }
        },
        error: function () {
            hideOverlay();
            showErrorGrowl('Something went wrong!', 'Unable to get the files for google drive. If the issue persists, please seek support');
        }
    });
}

function initializeScrollOnHover($select) {
    $select.selectpicker('refresh');
    $select.data('selectpicker').$menu.find('li a').each(function () {
        var $link = $(this);
        var $text = $link.find('span.text');
        // Bind to mouseenter.
        $link.on('mouseenter', function () {
            var diff = ($link.width() - $text.width());
            // If the text content is wider than the menu, animate the `text-indent`.
            if (diff < 0) {
                $text.stop(true).delay(250).animate({textIndent: diff + 'px'}, 500, "linear");
            }
        });

        // On mouseleave, animate the `text-indent` back to `0`.
        $link.on('mouseleave', function () {
            $text.stop(true).animate({textIndent: 0}, 250, "linear");
        });
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

function getFeatures() {
    return $.ajax({url: "/service/?name=features", type: 'GET', dataType: 'json', timeout: 10000});
}

function showLocality() {
    var locality = $('#locality').val();
    if (locality != undefined && locality != '') {
        var localityShown = false;
        $.each(layers, function (index, val) {
            if (val == locality) {
                localityShown = true;
                return false;
            }
        });
        if (localityShown)
            return false;
        console.log('making service call to bring up the locality');
        $.get("/service/?name=locality&city=" + locality, function (response, status) {
            map.setZoom(4);
            var heatMap = [];
            $.each(response, function (index, feature) {
                heatMap.push({
                    location: new google.maps.LatLng(feature.gps_abs_lat, feature.gps_abs_lon),
                    weight: feature.ch4 * 10
                });
            });
            var layer = new google.maps.visualization.HeatmapLayer({
                data: heatMap,
                radius: map.getZoom() * 3
            });
            layer.setMap(map);
            layers.push(locality);
        }, "json");
    }
}

// This method will be called by google maps api. No need to call it in document ready
function initMap() {
    //Enabling new cartography and themes
    google.maps.visualRefresh = true;
    //Setting starting options of map
    var mapOptions = {
        center: new google.maps.LatLng(38, -70),
        zoom: 4,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        panControl: false,
        zoomControl: true,
        scaleControl: true,
        streetViewControl: false,
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
    var mapElement = $('#mapDiv')[0];
    map = new google.maps.Map(mapElement, mapOptions);

    // Create the search box and link it to the UI element.
    var searchPlace = $('#searchPlace')[0];
    var autocomplete = new google.maps.places.Autocomplete(searchPlace);
    autocomplete.bindTo('bounds', map);
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(searchPlace);
    var infowindow = new google.maps.InfoWindow();
    var marker = new google.maps.Marker({
        map: map
    });
    marker.addListener('click', function () {
        infowindow.open(map, marker);
    });
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
            map.setZoom(10);
        }
    });

    map.addListener('zoom_changed', function () {
        zoom_changed = true;
    });

    map.addListener('idle', function () {
        //unhide floating div when the map loads completely
        $('#floatingDiv').removeClass('hidden');
    });

    var drawingManager = new google.maps.drawing.DrawingManager({
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.LEFT_BOTTOM,
            drawingModes: [
                google.maps.drawing.OverlayType.POLYGON,
                google.maps.drawing.OverlayType.RECTANGLE
            ]
        },
        polygonOptions: {
            fillOpacity: 0.0,
            strokeColor: '#FF0000',
            strokeWeight: 2
        },
        rectangleOptions: {
            fillOpacity: 0.0,
            strokeColor: '#FF0000',
            strokeWeight: 2
        }
    });
    drawingManager.setMap(map);
    google.maps.event.addListener(drawingManager, 'overlaycomplete', function (event) {
        drawingManager.setDrawingMode(null);//Default to hand
        //event.overlay.setOptions({fillOpacity: 0.0, strokeColor: '#FF0000'});
        if (event.type == google.maps.drawing.OverlayType.POLYGON) {
            var latlng = event.overlay.getPath().getArray(); //latlng array
            var polygon = "[";
            latlng.forEach(function (location, index) {
                polygon = polygon.concat("{\"lat\":\"" + location.lat() + "\",\"lon\":\"" + location.lng() + "\"}");
                if (index < latlng.length - 1)
                    polygon = polygon.concat(",");
            });
            polygon = polygon + "]";
            lastOverlay = event.overlay;
            lastPolygon = polygon;
            modalClosed = false;
            $('#polygon-name').val("");
            $('#polygon-modal').modal();
        } else {
            //overlay is a rectangle
            var bounds = event.overlay.getBounds();
            var ne = bounds.getNorthEast();
            var sw = bounds.getSouthWest();
            var polygon = '[{"lat":"' + ne.lat() + '","lon":"' + ne.lng() + '"},' +
                '{"lat":"' + sw.lat() + '","lon":"' + ne.lng() + '"},' +
                '{"lat":"' + sw.lat() + '","lon":"' + sw.lng() + '"},' +
                '{"lat":"' + ne.lat() + '","lon":"' + sw.lng() + '"}]';
            lastOverlay = event.overlay;
            lastPolygon = polygon;
            modalClosed = false;
            $('#polygon-name').val("");
            $('#polygon-modal').modal();
        }
    });
}


