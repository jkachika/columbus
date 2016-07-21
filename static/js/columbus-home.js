// The OAuth2.0 client ID from the Google Developers Console.
var SERVICE_HOST = "http://harrisburg.cs.colostate.edu:8787/columbus";
var CLIENT_ID = '492266571222-lk6vohmrf2fkkvkmjfi5583qj30ijjkc.apps.googleusercontent.com';
var APIKEY = "AIzaSyBmgPNSfhXOslSk0fRyf7t0NG7lZ5s7d8s";
var FUSION_TABLE_ID = "1hUiW58GkgIM1A5lWPeN4xwL1TXaxm7RMYaMsYt6s";
var map;
var ch4layer;
var ch4layerPosition;
var data = [];
var polygons = [];
var timer;
var ch4layers = {};
var geoJSON;
var showingData = false;
var zoom_changed = false;
// needed for handling polygon drawing
var lastPolygon;
var modalClosed;
var lastOverlay;
var yaxes = 1;
var axisoptions;
var axiscolors = ['#FF00FF', '#F88017', '#168EF7', '#006400'];

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
    // Attempt to authenticate for Earth Engine using existing credentials.
    // ee.data.authenticate(CLIENT_ID, initializeGEE, null, null, onImmediateFailed);
    initializeGEE();
    $("#polygon-name").keyup(function(event){
        if(event.keyCode == 13){
            $("#save-polygon").click();
        }
    });
    $('#save-polygon').click(function () {
        var polygonName = $('#polygon-name').val()
        if(polygonName != undefined && polygonName.length != 0 && lastPolygon != undefined){
            $('#polygon-modal').modal('hide');
            modalClosed = true;
            getFeatureset(polygonName, lastPolygon);
        }
    });

    $('#addY').click(function () {
        if(yaxes < 4) {
            yaxes++;
            $('#yaxes').append("<select id='y" + yaxes + "' class='selectpicker show-menu-arrow show-tick' data-size='5' data-width='24%'\
                            title='Choose a feature'>\
                             </select>&nbsp;");
            $('#y'+yaxes).html(axisoptions);
            $('#y'+yaxes).selectpicker('refresh');
        }
        return false;
    });

    $('#hideFeatures').click(function () {
        $('#hideFeatures').addClass('hidden');
        $('#features').addClass('hidden');
        $('#showFeatures').removeClass('hidden');
    });

    $('#showFeatures').click(function () {
        $('#hideFeatures').removeClass('hidden');
        $('#features').removeClass('hidden');
        $('#showFeatures').addClass('hidden');
    });

    var csrftoken = $.cookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    $('#polygonid').on('change', function(){
        var selected = $(this).find("option:selected").val();
        var polygon;
        $.each(polygons, function( index, obj) {
            if(obj.id == selected){
                polygon = obj;
                return false;
            }
        });
        if(polygon != undefined)
            showPolygonStats(polygon.stats);
    })

    $('#show-chart').on('click', function(){
        var selected = $('#polygonid').find("option:selected").val();
        var polygon;
        $.each(polygons, function(index, obj) {
            if(obj.id == selected){
                polygon = obj;
                return false;
            }
        });
        if(polygon != undefined) {
            var type = $('#chartid').val();
            if(type == undefined)
                type = 'line';
            var xval = buildChartXAxis();
            var yval = buildChartYAxis();
            var series = buildChartSeries(polygon.geoJSON);
            if(xval != 'undefined' && yval != undefined && yval.length != 0 && series != undefined && series.length != 0) {
                var xtext = xval.title.text;
                if (xtext == 'epoch_time' || xtext == 'datetime') {
                    showPolygonChart(polygon.name + ' Visual Analysis', type, xval, yval, series);
                    $($.browser.mozilla ? "html" : "body").animate({scrollTop: $("#chart-container").offset().top}, 500);
                } else
                    alert('Chosen x-axis(' + xtext + ') for charting is not supported as of now');
            } else {
                alert('One or more of the chosen options for charting are not supported as of now');
            }
        }
    })
});

$(document).on('click', '#fetchLocality', function () {
    var locality = $("#locality").val();
    if (ch4layers[locality] == undefined) {
        getLocality(locality);
    } else {
        $("#ch4").prop('checked', true);
        $("#ch4").trigger("change");
    }
});

var onImmediateFailed = function () {
    $('.g-sign-in').removeClass('hidden');
    $('.g-sign-in .button').click(function () {
        ee.data.authenticateViaPopup(function () {
            // If the login succeeds, hide the login button and run the analysis.
            $('.g-sign-in').addClass('hidden');
            $('#searchPlace').removeClass('hidden');
            $('#mapDiv').addClass('col-md-6 align-left');
            $('#optionsDiv').removeClass('hidden');
            $('#spinner').removeClass('hidden');
            initializeGEE();
        });
    });
};

var initializeGEE = function () {
    //$('#spinner').addClass('hidden');
    $('#searchPlace').removeClass('hidden');
    $('#mapDiv').addClass('col-md-6 align-left');
    $('#optionsDiv').removeClass('hidden');
    //ee.initialize();

    //var ftc = ee.FeatureCollection('ft:1hUiW58GkgIM1A5lWPeN4xwL1TXaxm7RMYaMsYt6s');
    /*var minch4 = ftc.aggregate_min('ch4');
     var maxch4 = ftc.aggregate_max('ch4');
     $('#ch4_heading').text("Methane (min: "+minch4.getInfo()+", max: "+maxch4.getInfo()+")");*/

    /*var ft = ee.Feature(ee.Geometry.LineString(ftc.geometry().geometries()));
     var mapId = ft.getMap({'color': 'FF0000'});
     var overlay = new ee.MapLayerOverlay(
     'https://earthengine.googleapis.com/map',
     mapId.mapid, mapId.token, {});*/

    // Show a count of the number of map tiles remaining.
    /*overlay.addTileCallback(function(event) {
     $('.tiles-loading').text(event.count + ' tiles remaining.');
     if (event.count === 0) {
     $('.tiles-loading').empty();
     }
     });*/

    // Show the EE map on the Google Map.
    /*map.overlayMapTypes.push(overlay);
     ch4layer = new google.maps.FusionTablesLayer({
     query: {
     select: 'gps_abs_lat',
     from: '1hUiW58GkgIM1A5lWPeN4xwL1TXaxm7RMYaMsYt6s'
     },
     styles: [{
     where: 'ch4 <= 2.0',
     markerOptions: {
     iconName: "small_yellow"
     }
     }, {
     where: 'ch4 > 2.0 and ch4 <= 2.5',
     markerOptions: {
     iconName: "small_green"
     }
     }, {
     where: 'ch4 > 2.5 and ch4 <= 3.0',
     markerOptions: {
     iconName: "small_purple"
     }
     }, {
     where: 'ch4 > 3.0',
     markerOptions: {
     iconName: "small_red"
     }
     }]
     });
     ch4layer.addListener('click', function(ftme) {
     ftme.infoWindowHtml = '<div class=\'googft-info-window\'> \
     <b>Platform Id: </b> '+ ftme.row['platform_id'].value +'<br> \
     <b>Date: </b> '+ ftme.row['date'].value +'<br> \
     <b>Time: </b> '+ ftme.row['time'].value +'<br> \
     <b>Cavity Pressure: </b>'+ ftme.row['cavity_pressure'].value +'<br> \
     <b>Cavity Temperature: </b> '+ ftme.row['cavity_temp'].value +'<br> \
     <b>Methane: </b> '+ ftme.row['ch4'].value +'<br> \
     <b>GPS Time: </b>'+ ftme.row['gps_time'].value +'<br> \
     <b>Wind North: </b>'+ ftme.row['wind_n'].value +'<br> \
     <b>Wind East: </b> '+ ftme.row['wind_e'].value +'<br> \
     <b>Car Speed: </b> '+ ftme.row['car_speed'].value +'<br> \
     <b>Postal Code: </b> '+ ftme.row['postal_code'].value +'<br> \
     <b>Locality: </b> '+ ftme.row['locality'].value + ' \
     </div>';
     });
     getFeatures(FUSION_TABLE_ID, APIKEY);*/
    //map.setCenter(new google.maps.LatLng(-122.1899, 37.5010));

    //Making a service call to Galileo
    $.when(getLocalities(), getFeatures()).done(function (localityArgs, featureArgs){
        // setting localities data
        var html = [];
        var data = localityArgs[0];
        $(data).each(function (index, val) {
            html.push("<option>" + val + "</option>");
        });
        $('#locality').html(html.join(''));
        $('#locality').selectpicker('refresh');


        // setting features data
        var count = 0;
        html = [];
        data = featureArgs[0];
        var options = [];
        var maxcolumns = 4;
        html.push('<table width="100%" class="features"><tr>');
        $(data).each(function (index, val) {
            options.push("<option>" + val + "</option>");
            html.push("<td valign='top' width='" + (100 / maxcolumns) + "%'><label class='checkbox-inline'><input id='" + val + "'  type='checkbox' value='" + val + "' onchange=doOverlay(this);>" + val + "</label></td>");
            count++;
            if (count % maxcolumns == 0)
                html.push("</tr><tr>");
        });
        html.push('</tr></table>');
        $('#features').append(html.join(''));
        axisoptions = options.join('');
        //$('#xaxis').html(axisoptions);
        $('#y1').html(axisoptions);
        //$('#xaxis').selectpicker('refresh');
        $('#y1').selectpicker('refresh');

        //hide the spinner
        $('#spinner').addClass('hidden');
    });
    /*var polygon = '[{ "lat" : "34.119479019268425", "lon" : "-117.81463623046875"},{ "lat" : "34.12544756511612", "lon" : "-117.54512786865234"},{ "lat" : "33.92285064485909", "lon" : "-117.5533676147461"},{ "lat" : "33.93139678750913", "lon" : "-117.83077239990234"}]';
     getFeatureset(polygon);*/
};

function doOverlay(feature) {
    if (feature.id == 'ch4') {
        if (feature.checked) {
            for (var key in ch4layers) {
                ch4layers[key].setMap(map);
            }
            /*map.overlayMapTypes.push(ch4layer);
             ch4layerPosition = map.overlayMapTypes.getLength() - 1;
             $('#feature_ch4').removeClass('hidden');*/
        } else {
            for (var key in ch4layers) {
                ch4layers[key].setMap(null);
            }
            /*map.overlayMapTypes.removeAt(ch4layerPosition);
             $('#feature_ch4').addClass('hidden');*/
        }
    }

}

function getLocalities() {
    $('#spinner').removeClass('hidden');
    //return $.ajax({url: SERVICE_HOST + "/locality?names", type: 'GET', dataType: 'json'});
    return $.ajax({url: "/service/?name=localities", type: 'GET', dataType: 'json'});
}


function getFeatures() {
    $('#spinner').removeClass('hidden');
    //return $.ajax({url: SERVICE_HOST + "/features", type:'GET', dataType: 'json'});
    return $.ajax({url: "/service/?name=features", type:'GET', dataType: 'json'});
}

function getLocality(locality) {
    $('#spinner').removeClass('hidden');
    //$.get(SERVICE_HOST + "/locality?featureset&locality=" + locality, function (response, status) {
    $.get("/service/?name=locality&city=" + locality, function (response, status) {
        map.setZoom(4);
        var heatMap = [];
        $.each(response, function (index, feature) {
            heatMap.push({
                location: new google.maps.LatLng(feature.gps_abs_lat, feature.gps_abs_lon),
                weight: feature.ch4 * 10
            });
        });
        ch4layers[locality] = new google.maps.visualization.HeatmapLayer({
            data: heatMap,
            radius: map.getZoom() * 3
        });
        $("#ch4").prop('checked', true);
        $("#ch4").trigger("change");
        $('#spinner').addClass('hidden');
    }, "json");
}

/*function getFeatures(ftid, apikey){
 $.get("https://www.googleapis.com/fusiontables/v1/tables/"+ftid+"/columns?key="+apikey, function(data, status){
 var count = 0;
 var html = [];
 var maxcolumns = 4;
 html.push('<table width="100%" class="features"><tr>');
 $.each(data.items, function(key, column){
 if(column.hasOwnProperty('description')){
 html.push("<td valign='top' width='"+(100/maxcolumns)+"%'><label class='checkbox-inline'><input id='" + column.name + "' type='checkbox' value='" + column.name + "' onchange=doOverlay(this);>"+ column.description +"</label></td>");
 count++;
 if(count % maxcolumns == 0)
 html.push("</tr><tr>");
 }
 });
 html.push('</tr></table>');
 $('#features').append(html.join(''));
 }, "json");
 }*/

function showPolygonStats(stats){
    var html = "<table class='table table-bordered'>\
                    <tbody>";
    var columns = 0;
    var statsPresent;
    $.each(stats, function(name, value){
        if(columns % 2 == 0) {
            if (columns == 0) html = html + "<tr>";
            else html = html + "</tr><tr>";
        }
        html = html + "<td width='25%' class='td-heading'>" + name + "</td>"
        html = html + "<td width='25%'>" + String(value).substring(0, 10) + "</td>"
        columns++;
        statsPresent = true;
    });
    html = html + "</tr></tbody></table>";
    if(statsPresent)
        $("#stats").html(html);
    else {
        $("#stats").html('No statistics found for the chosen polygon');
    }
}

function buildChartXAxis(){
    var xaxisVal = $('#xaxis').find("option:selected").val();
    if(xaxisVal != undefined && (xaxisVal == 'datetime' || xaxisVal == 'epoch_time')){
        return {
            title: {
                text: xaxisVal
            },
            type: 'datetime',
            labels: {
                formatter: function() {
                    return Highcharts.dateFormat('%I:%M %P', this.value);
                }
            },
            tickInterval: 5* 60 * 1000,
            lineWidth: 1,
            lineColor: '#92A8CD',
            tickWidth: 2,
            tickLength: 6,
            tickColor: '#92A8CD'
        };
    }
}

function buildChartYAxis(){
    var y = [];
    for (var i = 1; i <= yaxes; i++) {
       var yival =  $('#y'+i).find("option:selected").val();
       if(yival != 'undefined'){
            if(i % 2 == 0){
                y.push({title: { text: yival, style: {color: axiscolors[y.length]}}, opposite: true, lineColor: axiscolors[y.length], lineWidth: 2, tickWidth: 2, tickLength: 6});
            } else {
                y.push({title: { text: yival,  style: {color: axiscolors[y.length]}}, lineWidth: 2, lineColor: axiscolors[y.length], tickWidth: 2, tickLength: 6});
            }
       }
    }
    return y;

}

function buildChartSeries(geoJSON) {
    var xval = $('#xaxis').find("option:selected").val();
    var y = [];
    for (var i = 1; i <= yaxes; i++) {
        var yival = $('#y' + i).find("option:selected").val();
        if (yival != undefined)
            y.push(yival);
    }
    var series = []
    if(xval != undefined && y.length != 0){
        for(var i = 0; i < y.length; i++){
            var yval = y[i];
            data = [];
            $(geoJSON.features).each(function (index, feature) {
                var datum = [];
                datum.push(Number(feature.properties[xval]));
                datum.push(Number(feature.properties[yval]));
                data.push(datum);
            });
            series.push({name: yval, color:axiscolors[i], yAxis: i, data: data, lineWidth: 1})
        }
    }
    return series;
}

function showPolygonChart(chartTitle, chartType, xval, yval, series){

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
            xDateFormat: '%a, %Y %b %e - %I:%M:%S %P',
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


function getFeatureset(polygonName, polygon) {
    $('#spinner').removeClass('hidden');
    timer = new Date().getTime();
    $.ajax({
        method: "POST",
        dataType: "json",
        contentType: "application/json",
        url: "/featureset",
        data: polygon,
        success: function (response, status, xhr) {
            $('#spinner').addClass('hidden');
            if (map.getZoom() > 16) {
                map.data.addGeoJson(response.geoJSON);
            } else {
                geoJSON = response.geoJSON;
            }
            var polygonObj = {id: polygons.length, name: polygonName, geoJSON: response.geoJSON, stats: response.stats};
            polygons.push(polygonObj);
            $('#polygonid').append("<option value='" +polygonObj.id+ "'>"+polygonName + "</option>");
            $('#polygonid').selectpicker('refresh');
            $('#polygonid').selectpicker('val', polygonObj.id);
            $('#polygonid').trigger('change');

            //google chart
            /*var rows = [];
            $(response.geoJSON.features).each(function (index, feature) {
                var row = [];
                row.push((Number(feature.properties.epoch_time) - 1350000000) / 60000);
                row.push(Number(feature.properties.car_speed) / 5);
                row.push(Number(feature.properties.ch4));
                rows.push(row);
            });

            var epochBegin = rows[0][0];
            $(rows).each(function (index, row) {
                row[0] = parseInt(row[0] - epochBegin);
            });

            google.setOnLoadCallback(showChart(rows));*/


            /*var ttr = new Date().getTime();
             $('#ttr').append((ttr - timer) + " ms");
             $('#ttr').removeClass('hidden');
             $('#spinner').addClass('hidden');
             var ftc = ee.FeatureCollection(response);
             ftc = ftc.sort("epoch_time");
             var ft = ee.Feature(ee.Geometry.LineString(ftc.geometry().geometries()));
             var mapId = ft.getMap({'color': '00FFFF'});
             var overlay = new ee.MapLayerOverlay(
             'https://earthengine.googleapis.com/map',
             mapId.mapid, mapId.token, {});
             // Show the EE map on the Google Map.
             map.overlayMapTypes.push(overlay);

             var heatMap = [];
             $.each(response, function(index, feature) {
             heatMap.push({location: new google.maps.LatLng(feature.properties.gps_abs_lat, feature.properties.gps_abs_lon), weight: feature.properties.ch4 * 10});
             });*/

            /*var bufferch4 = function(feature){
             var ch4val = feature.get("ch4");
             ch4val = ee.Number.parse(ch4val).pow(2);
             return feature.buffer(ch4val);
             };

             bftc = ftc.map(bufferch4);*/
            /*mapId = bftc.getMap({'color': 'FFFF00'});
             ch4layer = new ee.MapLayerOverlay(
             'https://earthengine.googleapis.com/map',
             mapId.mapid, mapId.token, {});*/
            /*ch4layer = new google.maps.visualization.HeatmapLayer({
             data: heatMap,
             radius : map.getZoom()*3
             });
             var ttp = new Date().getTime();
             $('#ttp').append((ttp - ttr) + " ms");
             $('#ttp').removeClass('hidden');*/

        }
    });
}

//function to sort multidimensional arrays based on their first column
function comparator(a, b) {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    return 0;
}

function initMap() {
    //Enabling new cartography and themes
    google.maps.visualRefresh = true;
    //Setting starting options of map
    var mapOptions = {
        center: new google.maps.LatLng(38, -57),
        zoom: 4,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        panControl: false,
        zoomControl: true,
        scaleControl: true,
        streetViewControl: false,
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_RIGHT
        },
        zoomControlOptions: {
            style: google.maps.ZoomControlStyle.SMALL,
            position: google.maps.ControlPosition.TOP_LEFT
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
        $('#spinner').removeClass('hidden');
        if (document.getElementById('ch4').checked) {
            for (var key in ch4layers) {
                ch4layers[key].setOptions({radius: map.getZoom() * 3});
            }
        }
    });

    map.addListener('idle', function () {
        if (map.getZoom() > 16) {
            if (!showingData) {
                showingData = true;
                if (geoJSON != undefined) {
                    map.data.addGeoJson(geoJSON);
                    geoJSON = undefined;
                } else {
                    $(data).each(function (index, feature) {
                        map.data.add(feature);
                    });
                    data = [];
                }
            }
        } else {
            infowindow.close();
            if (showingData) {
                showingData = false;
                map.data.forEach(function (feature) {
                    data.push(feature);
                    map.data.remove(feature);
                });
            }
        }
        if(zoom_changed)
            $('#spinner').addClass('hidden');
    });
    map.data.setStyle({
        clickable: true,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 3,
            fillColor: '#FF00FF',
            fillOpacity: 1.0,
            strokeColor: '#FF00FF'
        }
    });
    map.data.addListener('click', function (event) {
        var f = event.feature;
        var iwHTML = '<div class=\'googft-info-window\'> \
		<b>Date: </b> ' + f.getProperty('date') + '<br> \
		<b>Time: </b> ' + f.getProperty('time') + '<br> \
		<b>Cavity Pressure: </b>' + f.getProperty('cavity_pressure') + '<br> \
		<b>Cavity Temperature: </b> ' + f.getProperty('cavity_temp') + '<br> \
		<b>Methane: </b> ' + f.getProperty('ch4') + ' ppm<br> \
		<b>Wind North: </b>' + f.getProperty('wind_n') + '<br> \
		<b>Wind East: </b> ' + f.getProperty('wind_e') + '<br> \
		<b>Car Speed: </b> ' + f.getProperty('car_speed') + ' mph<br> \
		<b>Postal Code: </b> ' + f.getProperty('postal_code') + '<br> \
		<b>Locality: </b> ' + f.getProperty('locality') + ' \
		</div>';
        infowindow.setContent(iwHTML);
        infowindow.setPosition(f.getGeometry().get());
        infowindow.open(map);
    });

    var drawingManager = new google.maps.drawing.DrawingManager({
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.RIGHT_BOTTOM,
            drawingModes: [
                //google.maps.drawing.OverlayType.MARKER,
                //google.maps.drawing.OverlayType.CIRCLE,
                google.maps.drawing.OverlayType.POLYGON,
                //google.maps.drawing.OverlayType.POLYLINE,
                google.maps.drawing.OverlayType.RECTANGLE
            ]
        }
        //markerOptions: {icon: 'images/beachflag.png'},
        /*circleOptions: {
         strokeWeight: 5,
         clickable: false,
         draggable: true,
         editable: true,
         zIndex: 1
         }*/
    });
    drawingManager.setMap(map);
    google.maps.event.addListener(drawingManager, 'overlaycomplete', function (event) {
        drawingManager.setDrawingMode(null);//Default to hand
        event.overlay.setOptions({fillOpacity: 0.0});
        /*if (event.type == google.maps.drawing.OverlayType.CIRCLE) {
         var radius = event.overlay.getRadius();
         }*/
        if (event.type == google.maps.drawing.OverlayType.POLYGON) {
            var latlng = event.overlay.getPath().getArray(); //latlng array
            var polygon = "[";
            latlng.forEach(function (location, index) {
                polygon = polygon.concat("{ \"lat\" : \"" + location.lat() + "\", \"lon\" : \"" + location.lng() + "\"}");
                if (index < latlng.length - 1)
                    polygon = polygon.concat(",");
            });
            polygon = polygon + "]";
            lastOverlay = event.overlay;
            lastPolygon = polygon;
            modalClosed = false;
            $('#polygon-name').val("");
            $('#polygon-modal').modal();
            //getFeatureset(polygon);
        } else {
            //overlay is a rectangle
            var bounds = event.overlay.getBounds();
            var ne = bounds.getNorthEast();
            var sw = bounds.getSouthWest();
            var polygon = '[{"lat" : "' + ne.lat() + '", "lon":"' + ne.lng() + '" },{"lat" : "' + sw.lat() + '", "lon":"' + ne.lng() + '" }, {"lat" : "' + sw.lat() + '", "lon":"' + sw.lng() + '" }, {"lat" : "' + ne.lat() + '", "lon":"' + sw.lng() + '" }]';
            lastOverlay = event.overlay;
            lastPolygon = polygon;
            modalClosed = false;
            $('#polygon-name').val("");
            $('#polygon-modal').modal();
            //getFeatureset(polygon);
        }
    });
}

$('#polygon-modal').on('shown.bs.modal', function () {
    $('#polygon-name').focus();
});

$('#polygon-modal').on('hidden.bs.modal', function () {
    if (!modalClosed && lastPolygon != undefined)
        lastOverlay.setMap(null);
});
