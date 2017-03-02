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

    //populating localities and features
    $.when(getLocalities(), getFeatures()).done(function (localityArgs, featureArgs) {
        var localities = localityArgs[0];
        var features = featureArgs[0];
        var html = [];
        $.each(localities, function (index, val) {
            html.push("<option>" + val + "</option>");
        });
        $('#locality').html(html.join(''));
        $('#locality').selectpicker('refresh');
        html = [];
        $.each(features, function (index, feature) {
            for (var name in feature) {
                html.push("<option data-type='" + feature[name] + "'>" + name + "</option>");
            }
        });
        $('#feature-label').html(html.join(''));
        $('#feature-label').selectpicker('refresh');
        isserviceup = true;
    }).fail(function (jqXHR, textStatus) {
        if (textStatus === 'timeout') {
            $.growl.error({
                title: 'Server timed out!',
                message: 'Galileo service is not available. If the issue persists, please seek support.',
                location: 'tc',
                delayOnHover: true,
                duration: 5000
            });
        } else {
            $.growl.error({
                title: 'Something went wrong!',
                message: 'Galileo service is not available. If the issue persists, please seek support.',
                location: 'tc',
                delayOnHover: true,
                duration: 5000
            });
        }
        isserviceup = false;
    });

    //set feature type based on the selected feature
    $('#feature-label').on('change', function () {
        var option = $(this).find('option:selected');
        $('#feature-type').val(option.data('type'));
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

    //draw chosen polygon on the map
    $('#polygon').on('change', function () {
        var option = $(this).find('option:selected');
        if (drewPolygon != undefined)
            drewPolygon.setMap(null);
        var paths = [];
        var bounds = new google.maps.LatLngBounds(); //bounding box of the polygon
        $.each(option.data('polygon'), function (index, item) {
            var lat = parseFloat(item.lat);
            var lng = parseFloat(item.lon);
            paths.push({'lat': lat, 'lng': lng});
            bounds.extend(new google.maps.LatLng(lat, lng));
        });
        // Construct the polygon.
        drewPolygon = new google.maps.Polygon({
            paths: paths,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillOpacity: 0.0
        });
        drewPolygon.setMap(map);
        //set map center to polygon center
        map.fitBounds(bounds);
    });
});

function validateForm() {
    var choice = $('input:radio[name=datasource]:checked').val()
    if (choice == 'locality') {
        var locality = $('#locality').val();
        if (locality == undefined || locality == '') {
            $('button[data-id=locality]').focus();
            return false;
        }
    } else if (choice == 'polygon') {
        var polygon = $('#polygon').val();
        if (polygon == undefined || polygon == '') {
            $('button[data-id=polygon]').focus();
            return false;
        }
    } else {
        var featureLabel = $('#feature-label').val();
        if (featureLabel == undefined || featureLabel == '') {
            $('button[data-id=feature-label]').focus();
            return false;
        }

        var $featureValue = $('#feature-value');
        if ($featureValue.val() == undefined || $featureValue.val().trim() == '') {
            $featureValue.val('');
            $featureValue.focus();
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
    if (choice == 'locality') {
        $('#locality').removeAttr('disabled').selectpicker('refresh');
        $('#show-on-map').removeAttr('disabled');
        $('#polygon').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-label').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-op').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-value').attr('disabled', 'true');
    } else if (choice == 'polygon') {
        $('#show-on-map').attr('disabled', 'true');
        $('#locality').attr('disabled', 'true').selectpicker('refresh');
        $('#polygon').removeAttr('disabled').selectpicker('refresh');
        $('#feature-label').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-op').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-value').attr('disabled', 'true');
    } else {
        $('#show-on-map').attr('disabled', 'true');
        $('#locality').attr('disabled', 'true').selectpicker('refresh');
        $('#polygon').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-label').removeAttr('disabled').selectpicker('refresh');
        $('#feature-op').removeAttr('disabled').selectpicker('refresh');
        $('#feature-value').removeAttr('disabled');
    }
}

function getLocalities() {
    return $.ajax({url: "/bigquery/?name=localities", type: 'GET', dataType: 'json', timeout: 10000});
}


function getFeatures() {
    return $.ajax({url: "/bigquery/?name=features", type: 'GET', dataType: 'json', timeout: 10000});
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
        $.get("/bigquery/?name=locality&city=" + locality, function (response, status) {
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


