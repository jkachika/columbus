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
var dataLayers = {};
var _drewPolygon;
var previousDataLayer;
var globalInfoWindow;
var frozenChoices = {};
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
    var $bqfeature = $('#bq-feature-label');
    $bqtable.on('change', function () {
        var table = $(this).val();
        $.ajax({
            url: "/bigquery/?name=features&table=" + table,
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
                $('#bq-feature-value').val('');
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
            url: "/elements/?name=constraint&source=bigquery&table=" + table,
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
            url: "/bigquery/?name=first&table=" + table + "&feature=" + feature,
            type: 'GET',
            dataType: 'json',
            timeout: 60000,
            success: function (response) {
                var suggestions = [];
                $.each(response.result.rows, function (index, feature) {
                    suggestions.push(feature[0]["v"]);
                });
                var $bqvalue = $('#bq-feature-value');
                $bqvalue.val('');
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
                    $('#galileo-spatial').append('<option value="' + response.id + '" data-polygon=\'' + response.json + '\'>'
                        + response.name + '</option>').selectpicker('refresh');
                    /*$('#polygon').append('<option value="' + response.id + '" data-polygon=\'' + response.json + '\'>'
                     + response.name + '</option>').selectpicker('refresh');*/
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

    //$("#start-flow-form").on('click', 'freeze-source', function () {
    //    freezeSource();
    //});

    $('#workflow').on('change', function () {
        var workflow = $(this).val();
        showOverlay();
        $.ajax({
            type: "GET",
            url: "/data/?source=workflow&id=" + workflow,
            dataType: 'json',
            success: function (response) {
                hideOverlay();
                frozenChoices = {'workflow': workflow};
                if (response.what == 'components') {
                    var components = response.result;
                    var html = [];
                    frozenChoices.components = components;
                    frozenChoices.frozen = {}
                    $(components).each(function (index, component) {
                        if (index == 0)
                            html.push('<option value="' + component.id + '" selected>' + component.name + '</option>');
                        else
                            html.push('<option value="' + component.id + '">' + component.name + '</option>');
                    });
                    var $rootComponents = $('#root-components');
                    if (html.length == 0) {
                        $rootComponents.html('');
                        $rootComponents.prop('disabled', true).selectpicker('refresh');
                        $("#datasource > option").each(function () {
                            if ($(this).attr('value') == "combiner")
                                $(this).removeAttr('disabled');
                            else
                                $(this).prop('disabled', true);
                        });
                    } else {
                        $rootComponents.removeAttr('disabled');
                        $rootComponents.html(html.join(''));
                        initializeScrollOnHover($rootComponents);
                        $("#datasource > option").each(function () {
                            if ($(this).attr('value') == "combiner") {
                                $(this).prop('disabled', true);
                            } else
                                $(this).removeAttr('disabled');
                        });
                    }
                    $('#datasource').val('').selectpicker('refresh');
                    $('#bq-details-div').addClass('hidden');
                    $('#combiner-title').addClass('hidden');
                    $('#gd-details-div').addClass('hidden');
                    $('#galileo-details-div').addClass('hidden');
                    $('#frozen-component-wrapper').addClass('hidden');
                    clearGalileoParams();
                    $('div#legendDiv').addClass('hidden');
                } else if (response.what == 'error') {
                    showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, ' +
                        'please seek support.');
                }
            },
            error: function () {
                hideOverlay();
                showErrorGrowl('Something went wrong!', 'Unable to get the files for google drive. ' +
                    'If the issue persists, please seek support')
            }
        });
    });

    $('#galileo-filesystem').on('change', function () {
        addDataLayer($(this).val());
        $.ajax({
            url: "/elements/?name=constraint&source=galileo&table=" + $(this).val(),
            type: 'GET',
            dataType: 'json',
            timeout: 10000,
            success: function (response) {
                var html = [];
                $.each(response.result, function (index, constraint) {
                    html.push("<option value='" + constraint.id + "'>" + constraint.name + "</option>");
                });
                html = html.join('');
                var $gconstraint = $('#galileo-constraint');
                $gconstraint.html(html);
                initializeScrollOnHover($gconstraint);
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

    $('#galileo-spatial').on('change', function () {
        var polygonJSON = $(this).find("option:selected").data("polygon");
        if (_drewPolygon != undefined)
            _drewPolygon.setMap(null);
        var paths = [];
        var bounds = new google.maps.LatLngBounds(); //bounding box of the polygon
        $.each(polygonJSON, function (index, item) {
            var lat = parseFloat(item.lat);
            var lng = parseFloat(item.lon);
            paths.push({'lat': lat, 'lng': lng});
            bounds.extend(new google.maps.LatLng(lat, lng));
        });
        // Construct the polygon.
        _drewPolygon = new google.maps.Polygon({
            paths: paths,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillOpacity: 0.0,
            clickable: false
        });
        _drewPolygon.setMap(map);
        //set map center to polygon center
        map.fitBounds(bounds);
    });

    $('#root-components').on('change', function () {
        var root = $(this).val();
        if ('frozen' in frozenChoices && root in frozenChoices.frozen) {
            var choice = frozenChoices.frozen[root];
            if (choice.source == 'drive') {
                $('input:radio[name=gd-run-type]').prop('checked', false);
                $('input:radio[name=gd-run-type][value=' + choice.runType + ']').prop('checked', true);
            }
            $('#datasource').val(choice.source).selectpicker('refresh').trigger('change');
            var datasourceChanged = false;
            var tableChanged = false;
            var featureChanged = false;
            var filesystemChanged = false;
            $(document).ajaxStop(function () {
                if (choice.source == 'bigquery') {
                    if (datasourceChanged)
                        return;
                    $('#bq-table').val(choice.identifier).selectpicker('refresh').trigger('change');
                    datasourceChanged = true;
                    $(document).ajaxStop(function () {
                        if (tableChanged)
                            return;
                        $('input:radio[name=run-type]').prop('checked', false);
                        $('input:radio[name=run-type][value=' + choice.runType + ']').prop('checked', true).trigger('click');
                        $('#bq-feature-label').val(choice.feature).selectpicker('refresh').trigger('change');
                        tableChanged = true;
                        $(document).ajaxStop(function () {
                            if (featureChanged)
                                return;
                            $('#bq-feature-type').val(choice.primitive);
                            $('#bq-feature-op').val(choice.op).selectpicker('refresh');
                            $('#bq-feature-value').val(choice.value);
                            $('#bq-constraint').val(choice.constraint).selectpicker('refresh');
                            featureChanged = true;
                        });
                    });
                } else if (choice.source == 'drive') {
                    if (datasourceChanged)
                        return;
                    $('#gd-identifier').val(choice.identifier).selectpicker('refresh');
                    datasourceChanged = true;
                } else if (choice.source == 'galileo') {
                    if (datasourceChanged)
                        return;
                    $('#galileo-filesystem').val(choice.identifier).selectpicker('refresh').trigger('change');
                    datasourceChanged = true;
                    $(document).ajaxStop(function () {
                        if (filesystemChanged)
                            return;
                        $('input:radio[name=galileo-run-type]').prop('checked', false);
                        $('input:radio[name=galileo-run-type][value=' + choice.runType + ']').prop('checked', true);
                        $('#galileo-spatial').val(choice.spatial).selectpicker('refresh').trigger('change');
                        $('#galileo-temporal-year').val(choice.year);
                        $('#galileo-temporal-month').val(choice.month);
                        $('#galileo-temporal-day').val(choice.day);
                        $('#galileo-temporal-hour').val(choice.hour);
                        $('#galileo-constraint').val(choice.constraint).selectpicker('refresh');
                        filesystemChanged = true;
                    });
                }
            });
            if (choice.source == 'component') {
                $('#frozen-component').val(choice.component).selectpicker('refresh');
            }
        } else {
            $('#datasource').val('').selectpicker('refresh');
            $('#bq-details-div').addClass('hidden');
            $('#combiner-title').addClass('hidden');
            $('#gd-details-div').addClass('hidden');
            $('#galileo-details-div').addClass('hidden');
            $('#frozen-component-wrapper').addClass('hidden');
            clearGalileoParams();
            $('div#legendDiv').addClass('hidden');
        }
    });
});

function freezeSource() {
    var workflow = $('#workflow').val();
    if (workflow == undefined || workflow == '') {
        $('button[data-id=workflow]').focus();
        return false;
    }
    var $rootComponents = $('#root-components');
    var root = $rootComponents.val();
    if (root == undefined || root == '') {
        $('button[data-id=root-components]').focus();
        return false;
    }
    var choice = $('#datasource').val();
    if (choice == 'undefined' || choice == '') {
        $('button[data-id=datasource]').focus();
        return false;
    }
    if (choice == 'bigquery') {
        var $bqtable = $('#bq-table');
        var runType = $('input:radio[name=run-type]:checked').val();
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
    } else if (choice == 'component') {
        var $frozenComponent = $('#frozen-component');
        if ($frozenComponent.val() == undefined || $frozenComponent.val() == '') {
            $('button[data-id=frozen-component]').focus();
            return false;
        }
    } else if (choice == 'galileo') {
        var $galileoFilesystem = $('#galileo-filesystem');
        if ($galileoFilesystem.val() == undefined || $galileoFilesystem.val() == '') {
            //$('button[data-id=galileo-filesystem]').focus();
            //return false;
        }
        var galileoRunType = $('input:radio[name=galileo-run-type]:checked').val();
        var $galileoSpatial = $('#galileo-spatial');
        var $galileoTemporalYear = $('#galileo-temporal-year');
        var $galileoTemporalMonth = $('#galileo-temporal-month');
        var $galileoTemporalDay = $('#galileo-temporal-day');
        var $galileoTemporalHour = $('#galileo-temporal-hour');
        var spaceOrTime = false;
        if ($galileoSpatial.val() != undefined && $galileoSpatial.val() != '') {
            spaceOrTime = true;
        }
        if ($galileoTemporalYear.val() != undefined && $galileoTemporalYear.val() != '') {
            spaceOrTime = true;
            var year = $galileoTemporalYear.val();
            if (!(/^(19|20)[0-9]{2}$/.test(year))) {
                $galileoTemporalYear.val('').focus();
                return false;
            }
        }
        if ($galileoTemporalMonth.val() != undefined && $galileoTemporalMonth.val() != '') {
            spaceOrTime = true;
            var month = $galileoTemporalMonth.val();
            if (!/^(0[1-9]|1[0-2])$/.test(month)) {
                $galileoTemporalMonth.val('').focus();
                return false;
            }
        }
        if ($galileoTemporalDay.val() != undefined && $galileoTemporalDay.val() != '') {
            spaceOrTime = true;
            var day = $galileoTemporalDay.val();
            if (!/^(0[1-9]|[12][0-9]|3[01])$/.test(day)) {
                $galileoTemporalDay.val('').focus();
                return false;
            }
        }
        if ($galileoTemporalHour.val() != undefined && $galileoTemporalHour.val() != '') {
            spaceOrTime = true;
            var hour = $galileoTemporalHour.val();
            if (!/^([01][1-9]|2[0-3])$/.test(hour)) {
                $galileoTemporalHour.val('').focus();
                return false;
            }
        }
        if (!spaceOrTime) {
            showErrorGrowl("Galileo Datasource",
                "Please choose a polygon or specify either an year, month, day or hour. " +
                "You can also specify all of them.");
            return false;
        }
    }
    $rootComponents.find("option").each(function () {
        if ($(this).attr('value') == root) {
            $(this).attr('data-content', "<b>" + $(this).html() + "</b>");
            frozenChoices.frozen[root] = {source: choice};
            if (choice == 'bigquery') {
                frozenChoices.frozen[root].identifier = $bqtable.val();
                frozenChoices.frozen[root].runType = runType;
                frozenChoices.frozen[root].feature = $bqfeature.val();
                frozenChoices.frozen[root].primitive = $('#bq-feature-type').val();
                frozenChoices.frozen[root].op = $('#bq-feature-op').val();
                frozenChoices.frozen[root].value = $('#bq-feature-value').val();
                frozenChoices.frozen[root].constraint = $('#bq-constraint').val();
            } else if (choice == 'drive') {
                frozenChoices.frozen[root].identifier = $gdIdentifier.val();
                frozenChoices.frozen[root].runType = $('input:radio[name=gd-run-type]:checked').val();
            } else if (choice == 'component') {
                frozenChoices.frozen[root].component = $('#frozen-component').val();
            } else if (choice == 'galileo') {
                frozenChoices.frozen[root].identifier = $galileoFilesystem.val();
                frozenChoices.frozen[root].runType = galileoRunType;
                frozenChoices.frozen[root].spatial = $galileoSpatial.val();
                frozenChoices.frozen[root].year = $galileoTemporalYear.val();
                frozenChoices.frozen[root].month = $galileoTemporalMonth.val();
                frozenChoices.frozen[root].day = $galileoTemporalDay.val();
                frozenChoices.frozen[root].hour = $galileoTemporalHour.val();
                frozenChoices.frozen[root].constraint = $('#galileo-constraint').val();
            }
            return false;
        }
    });
    $rootComponents.selectpicker('refresh');
    return true;
}


function findCycle(frozenComponent, allFrozenComponents = []) {
    if (allFrozenComponents.indexOf(frozenComponent.component) != -1)
        throw "Cycle Found in the Data source selection";
    else {
        allFrozenComponents.push(frozenComponent.component)
        if (frozenChoices.frozen[frozenComponent.component].source == 'component')
            findCycle(frozenChoices.frozen[frozenComponent.component], allFrozenComponents);
    }
}

function validateForm() {
    var workflow = $('#workflow').val();
    if (workflow == undefined || workflow == '') {
        $('button[data-id=workflow]').focus();
        return false;
    }
    $(frozenChoices.components).each(function (index, component) {
        if (!(component.id in frozenChoices.frozen)) {
            showErrorGrowl("Freeze Components", "Not all root components of the selected workflow " +
                "have a data source. Please select each root component, make data source choice, " +
                "freeze the component and then start the flow.");
            return false;
        }
    });
    try {
        $.each(frozenChoices.frozen, function (componentId, frozenChoice) {
            if (frozenChoice.source == 'component')
                findCycle(frozenChoice, []);
        });
    } catch (e) {
        showErrorGrowl("Cycle Found", "A cyclic dependency exists in the selection of data sources " +
            "of the root components. Please correct.");
        return false;
    }
    showOverlay();
    var identifyInstances = $.ajax({
        type: 'POST',
        url: "/startflow",
        data: {flowChoices: JSON.stringify(frozenChoices)},
        dataType: "json",
        success: function (response) {
            if (response.what == "error")
                showErrorGrowl("Something went wrong!", response.message);
            else if (response.what == "instances") {
                $('#review-flow').submit();
            }
        }
    });
    identifyInstances.error(function () {
        hideOverlay();
        showErrorGrowl("Something went wrong!", "An unknown error occurred. If the issue persists, please seek support.");
    });
    return false;
}

function chooseDatasource(choice) {
    clearGalileoParams();
    if (choice == 'bigquery') {
        $('#bq-details-div').removeClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
        $('#galileo-details-div').addClass('hidden');
        $('#frozen-component-wrapper').addClass('hidden');
        $('div#legendDiv').addClass('hidden');
        $.ajax({
            url: "/bigquery/?name=tables",
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
                var $bqtable = $('#bq-table');
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
    } else if (choice == 'drive') {
        $('#bq-details-div').addClass('hidden');
        $('#gd-details-div').removeClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#galileo-details-div').addClass('hidden');
        $('#frozen-component-wrapper').addClass('hidden');
        $('div#legendDiv').addClass('hidden');
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
                    showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, ' +
                        'please seek support.');
                }
            },
            error: function () {
                hideOverlay();
                showErrorGrowl('Something went wrong!', 'Unable to get the files for google drive. ' +
                    'If the issue persists, please seek support')
            }
        });
    } else if (choice == "combiner") {
        $('#bq-details-div').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
        $('#combiner-title').removeClass('hidden');
        $('#galileo-details-div').addClass('hidden');
        $('#frozen-component-wrapper').addClass('hidden');
        $('div#legendDiv').addClass('hidden');
    } else if (choice == 'component') {
        $('#bq-details-div').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#galileo-details-div').addClass('hidden');
        $('#frozen-component-wrapper').removeClass('hidden');
        $('div#legendDiv').addClass('hidden');
        var $frozenComponent = $('#frozen-component');
        var html = [];
        var selectedRoot = $('#root-components').val();
        $.each(frozenChoices.frozen, function (componentId, frozenChoice) {
            if (componentId != selectedRoot) {
                $(frozenChoices.components).each(function (index, component) {
                    if (componentId == component.id) {
                        html.push('<option value="' + component.id + '">' + component.name + '</option>');
                        return false;
                    }
                });
            }
        });
        $frozenComponent.html(html.join(""));
        initializeScrollOnHover($frozenComponent);
    } else if (choice == "galileo") {
        $('#bq-details-div').addClass('hidden');
        $('#gd-details-div').addClass('hidden');
        $('#combiner-title').addClass('hidden');
        $('#frozen-component-wrapper').addClass('hidden');
        $('#galileo-details-div').removeClass('hidden');
        $.ajax({
            type: "GET",
            url: "/galileo/?route=filesystem&q=names",
            dataType: 'json',
            success: function (response) {
                hideOverlay();
                if (response.what == 'filesystem#names') {
                    var filesystems = response.result;
                    var html = [];
                    $(filesystems).each(function (index, filesystem) {
                        html.push('<option value="' + filesystem.name + '" data-earliest="' + filesystem.earliestTime +
                            '" data-latest="' + filesystem.latestTime + '">' + filesystem.name + '</option>');
                    });
                    var $galileoFS = $('#galileo-filesystem');
                    $galileoFS.html(html.join(''));
                    initializeScrollOnHover($galileoFS);
                } else if (response.what == 'error') {
                    showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, ' +
                        'please seek support.');
                }
            },
            error: function () {
                hideOverlay();
                showErrorGrowl('Something went wrong!', 'Unable to get the filesystem details from Galileo. ' +
                    'If the issue persists, please seek support');
            }
        });
    }
}

function clearGalileoParams() {
    if (previousDataLayer != undefined)
        previousDataLayer.setMap(null);

    if (lastOverlay != undefined)
        lastOverlay.setMap(null);

    if (_drewPolygon != undefined)
        _drewPolygon.setMap(null);

    $('#galileo-spatial').val('').selectpicker('refresh');
    $('#galileo-temporal-year').val('');
    $('#galileo-temporal-month').val('');
    $('#galileo-temporal-day').val('');
    $('#galileo-temporal-hour').val('');
    $('#galileo-constraint').val('').selectpicker('refresh');
}

function addDataLayer(fsName) {
    clearGalileoParams();
    if (fsName in dataLayers) {
        previousDataLayer = dataLayers[fsName];
        previousDataLayer.setMap(map);
        $('div#legendDiv').removeClass('hidden');
    } else {
        $.ajax({
            type: "GET",
            url: "/galileo/?route=filesystem&q=overview&name=" + fsName,
            dataType: 'json',
            success: function (response) {
                hideOverlay();
                if (response.what == 'filesystem#overview') {
                    // Load GeoJSON.
                    var dataLayer = new google.maps.Data();
                    //dataLayer.loadGeoJson('https://quarkbackend.com/getfile/johnsoncharles26/overview');
                    dataLayer.addGeoJson(response.result[0][fsName]);

                    // Set the stroke width, and fill color for each polygon
                    dataLayer.setStyle(function (feature) {
                        var percent = feature.getProperty("blocks") / feature.getProperty("max-blocks");
                        var hexColor = colorGenerator(percent);
                        return {fillColor: "#" + hexColor, strokeWeight: 1, fillOpacity: 0.5};
                    });

                    google.maps.event.addListener(dataLayer, 'click', function (event) {
                        var region = event.feature.getProperty("region");
                        var blocks = event.feature.getProperty("blocks");
                        var fileSize = event.feature.getProperty("filesize");
                        var lastVisited = event.feature.getProperty("last-visited");
                        var myHTML = "<div style='text-align:left; font-family: sans-serif;'>" +
                            "<table style='table-layout: fixed; width: 280px; padding:6px 3px;" +
                            "border-collapse: collapse; border-spacing: 0; border-color: #ccc;'>" +
                            "<tr><td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#f0f0f0;'>Region</td>" +
                            "<td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#ffffff;'><b>" + region + "</b></td>" +
                            "<td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#f0f0f0;'>Filesize</td>" +
                            "<td width='55px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#ffffff;'><b>" + fileSize + "</b></td></tr><tr>" +
                            "<td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#f0f0f0;'>Blocks</td>" +
                            "<td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#ffffff;'><b>" + blocks + "</b></td>" +
                            "<td width='50px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#f0f0f0;'>Latest</td>" +
                            "<td width='55px' style='padding:6px 3px; border:1px solid #ccc; overflow:hidden; word-break:normal; " +
                            "color:#333;background-color:#ffffff;'><b>" + lastVisited + "</b></td></tr>" +
                            "</table></div>";
                        globalInfoWindow.setContent("<div style='width:280px; text-align: center;'>" + myHTML + "</div>");
                        var linearRing = event.feature.getGeometry().getAt(0);
                        var upperLeft = linearRing.getAt(0);
                        var lowerRight = linearRing.getAt(linearRing.getLength() - 2);
                        var position = new google.maps.LatLng((upperLeft.lat() + lowerRight.lat()) / 2,
                            (upperLeft.lng() + lowerRight.lng()) / 2);
                        globalInfoWindow.setPosition(position);
                        //infowindow.setOptions({pixelOffset: new google.maps.Size(0, -30)});
                        globalInfoWindow.open(map);
                    });

                    dataLayers[fsName] = dataLayer;
                    previousDataLayer = dataLayer;
                    previousDataLayer.setMap(map);
                    $('div#legendDiv').removeClass('hidden');
                } else if (response.what == 'error') {
                    showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, please seek support.');
                }
            },
            error: function () {
                hideOverlay();
                showErrorGrowl('Something went wrong!', 'Unable to get the filesystem details from Galileo. If the issue persists, please seek support');
            }
        });
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

/*function getFeatures() {
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
 }*/

function toHex(n) {
    var hex = n.toString(16);
    while (hex.length < 2) {
        hex = "0" + hex;
    }
    return hex;
}
function hslToRgb(hue, sat, light) {
    var t1, t2, r, g, b;
    hue = hue / 60;
    if (light <= 0.5) {
        t2 = light * (sat + 1);
    } else {
        t2 = light + sat - (light * sat);
    }
    t1 = light * 2 - t2;
    r = hueToRgb(t1, t2, hue + 2) * 255;
    g = hueToRgb(t1, t2, hue) * 255;
    b = hueToRgb(t1, t2, hue - 2) * 255;
    return {r: Math.floor(r), g: Math.floor(g), b: Math.floor(b)};
}
function hueToRgb(t1, t2, hue) {
    if (hue < 0) hue += 6;
    if (hue >= 6) hue -= 6;
    if (hue < 1) return (t2 - t1) * hue + t1;
    else if (hue < 3) return t2;
    else if (hue < 4) return (t2 - t1) * (4 - hue) + t1;
    else return t1;
}

function colorGenerator(percent) {
    var rgb = hslToRgb(Math.floor(percent * 300 + 60), 1, 0.5);
    return toHex(rgb.r) + toHex(rgb.g) + toHex(rgb.b);
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
    globalInfoWindow = infowindow;
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
        var polygon;
        if (event.type == google.maps.drawing.OverlayType.POLYGON) {
            var latlng = event.overlay.getPath().getArray(); //latlng array
            polygon = "[";
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
            polygon = '[{"lat":"' + ne.lat() + '","lon":"' + ne.lng() + '"},' +
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

    google.maps.event.addListener(map, 'click', function () {
        infowindow.close();
    });

    var legendHTML = [];
    for (var i = 0; i <= 25; ++i) {
        legendHTML.push('<span style="color: #' + colorGenerator(i / 25) + '">&#9608;</span>');
    }
    $('div#colorLegend').html(legendHTML.join(""));
}


