/**
 * Created by JohnsonCharles on 13-04-2016.
 */
var map;
var _lastPolygon;
var _drewPolygon;
var _lastCondition;
var _lastSchedule;
var _jpolylistwrapper;
var _jcondlistwrapper;
var _jschdlistwrapper;

var _bqtablesInitialized;

var _clipboard;

var _jcformwrapper;
var _jclistwrapper;
var _jeditorwrapper;
var _jeditor;
var _aceeditor;
var _lastcomponent;
var _opencomponent;
var _cref;
var _mref;
var _cparent;
var _cparties;
var _mparties;
var _wviewers;
var _cparentwell;
var _cpartieswell;
var _mpartieswell;
var _wviewerswell;
var _cparentoptions;
var _editormessage = '# Refer to documentation for the usage';

var _jwformwrapper;
var _jwlistwrapper;
var _jworkflowwrapper;
var _jwtimeline;
var _jwflowheight;
var _jwcomponents;
var _cdtimeline;
var _openworkflow;
var _lastworkflow;
var _flowplaceholder;

var _jmlistwrapper;
var _jmformwrapper;
var _jmeditorwrapper;
var _jmeditor;
var _acecombiner;
var _lastcombiner;
var _opencombiner;


$(document).ready(function () {

    //showing overlay for any ajax request
    $(document).ajaxStart(function () {
        showOverlay();
    });

    //hiding overlay after all ajax request complete
    $(document).ajaxStop(function () {
        hideOverlay();
    });

    var padval = $('#workspace-tabs').css('margin-top');
    $('#workspace-tabs').css({'margin-top': '0px', 'padding-top': padval});
    _jclistwrapper = $("#component-listwrapper");
    _jeditorwrapper = $('#editor-wrapper');
    _jcformwrapper = $('#component-formwrapper');
    _jeditor = $('#editor');

    _jmlistwrapper = $("#combiner-listwrapper");
    _jmformwrapper = $("#combiner-formwrapper");
    _jmeditorwrapper = $("#meditor-wrapper");
    _jmeditor = $('#meditor');

    _jwlistwrapper = $("#workflow-listwrapper");
    _jwformwrapper = $('#workflow-formwrapper');
    _jworkflowwrapper = $('#workflow-flowwrapper');
    _jwtimeline = $('#workflow-timeline');
    _cdtimeline = $('#cd-timeline');
    _jwflowheight = parseFloat(_jworkflowwrapper.css('height'));
    _jwcomponents = $('#wcomponents');
    _flowplaceholder = $('#flow-placeholder');

    _jpolylistwrapper = $("#polygon-listwrapper");
    _jcondlistwrapper = $("#condition-listwrapper");
    _jschdlistwrapper = $("#schedule-listwrapper");

    _clipboard = new Clipboard(document.querySelectorAll('aside'));

    resizeWrappers();
    ace.require("ace/ext/language_tools");
    var editors = [_aceeditor, _acecombiner];
    $(editors).each(function (index, editor) {
        editor = ace.edit(index == 0 ? "editor" : "meditor");
        editor.setTheme("ace/theme/monokai");
        editor.$blockScrolling = Infinity;
        editor.getSession().setMode("ace/mode/python");
        // enable autocompletion and snippets
        editor.setOptions({
            enableBasicAutocompletion: true,
            enableSnippets: true,
            enableLiveAutocompletion: false,
        });
        editor.getSession().setValue(_editormessage);
        editors[index] = editor;
    });
    _aceeditor = editors[0];
    _acecombiner = editors[1];
    $("#component-alert-holder").on('closed.bs.alert', function () {
        _jcformwrapper.nanoScroller({destroy: true});
        _jcformwrapper.nanoScroller();
    });
    $("#workflow-alert-holder").on('closed.bs.alert', function () {
        _jwformwrapper.nanoScroller({destroy: true});
        _jwformwrapper.nanoScroller();
    });
    $(window).resize(function () {
        resizeWrappers();
    });

    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        var target = $(e.target).attr("href") // activated tab
        resizeWrappers();
        initializeTabChange(target);
    });

    $('#cvis').change(function () {
        if ($(this).is(':checked'))
            $('#cparties-div').removeClass('hidden');
        else
            $('#cparties-div').addClass('hidden');
    });

    $('#mvis').change(function () {
        if ($(this).is(':checked'))
            $('#mparties-div').removeClass('hidden');
        else
            $('#mparties-div').addClass('hidden');
    });

    $('#wshare').change(function () {
        if ($(this).is(':checked'))
            $('#wviewers-div').removeClass('hidden');
        else
            $('#wviewers-div').addClass('hidden');
    });

    $('#croot').change(function () {
        if ($(this).is(':checked')) {
            $('#cparent-div').addClass('hidden');
            $('#poutput-div').addClass('hidden');
        }
        else {
            $('#cparent-div').removeClass('hidden');
            $('#poutput-div').removeClass('hidden');
        }
    });

    _cref = $('#component-ref');
    _mref = $('#combiner-ref');
    _cparentwell = $('#cparent-well');
    _cparent = $('#cparent');
    _cparties = $('#cparties');
    _mparties = $('#mparties');
    _wviewers = $('#wviewers');
    _cpartieswell = $('#cparties-well');
    _mpartieswell = $('#mparties-well');
    _wviewerswell = $('#wviewers-well');
    _cparentoptions = $('#cparent > option');
    _cparent.on('change', function () {
        /*$('div.bootstrap-select:first').css({
         'border': '',
         'border-radius': ''
         });
         $('div.bootstrap-select:first .btn:focus').css({
         'outline': '',
         '-webkit-box-shadow': '', 'box-shadow': ''
         });*/
        var selected = _cparent.val();

        if (selected == null) {
            _cparent.selectpicker('val', '');
            _cparentwell.addClass('hidden');
            $('#poutput').val('');
            return;
        }

        var type = "";
        var output = "";
        var html = [];
        var count = selected.length - 1;

        $(selected).each(function (index, val) {
            var result = val.split("-");
            var option = _cparent.find('option[value=' + val + ']').text();
            var ribbon = 'blue-ribbon';
            var reqDiv = $("#cid-" + result[1]);
            if (result[0] == "combiner") {
                ribbon = 'yellow-ribbon';
                reqDiv = $("#mid-" + result[1]);
            }
            type = reqDiv.data('type');
            html.push(option + "<aside data-clipboard-text='" + val + "' title='Click to copy' " +
                "class='" + ribbon + "'>" + val + "</aside><span style='font-size: 9px; color: grey; display: block'>" +
                type + "</span>");
            if (index < count)
                html.push('<hr style="margin-top: 5px;">');
            output = output + option + ": \n" + reqDiv.data('output') + "\n\n";
        });

        $('#poutput').val(output.substring(0, output.length - 2));

        _cparentwell.html(html.join('\n'));
        _cparentwell.removeClass('hidden');
        _clipboard.destroy();
        _clipboard = new Clipboard(document.querySelectorAll('aside'));
    });

    _cparties.on('change', function () {
        var selected = _cparties.val();
        if (selected == null) {
            _cparties.selectpicker('val', '');
            _cpartieswell.addClass('hidden');
            return;
        }
        var html = [];
        var count = selected.length - 1;
        $(selected).each(function (index, val) {
            var $option = _cparties.find('option[value=' + val + ']');
            html.push($option.text() + "<span style='font-size: 9px; color: grey; display: block'>" +
                $option.data("email") + "</span>");
            if (index < count)
                html.push('<hr style="margin-top: 5px; margin-bottom: 5px;">');
        });
        _cpartieswell.html(html.join('\n'));
        _cpartieswell.removeClass('hidden');
    });

    _mparties.on('change', function () {
        var selected = _mparties.val();
        if (selected == null) {
            _mparties.selectpicker('val', '');
            _mpartieswell.addClass('hidden');
            return;
        }
        var html = [];
        var count = selected.length - 1;
        $(selected).each(function (index, val) {
            var $option = _mparties.find('option[value=' + val + ']');
            html.push($option.text() + "<span style='font-size: 9px; color: grey; display: block'>" +
                $option.data("email") + "</span>");
            if (index < count)
                html.push('<hr style="margin-top: 5px; margin-bottom: 5px;">');
        });
        _mpartieswell.html(html.join('\n'));
        _mpartieswell.removeClass('hidden');
    });

    _wviewers.on('change', function () {
        var selected = _wviewers.val();
        if (selected == null) {
            _wviewers.selectpicker('val', '');
            _wviewerswell.addClass('hidden');
            return;
        }
        var html = [];
        var count = selected.length - 1;
        $(selected).each(function (index, val) {
            var $option = _wviewers.find('option[value=' + val + ']');
            html.push($option.text() + "<span style='font-size: 9px; color: grey; display: block'>" +
                $option.data("email") + "</span>");
            if (index < count)
                html.push('<hr style="margin-top: 5px; margin-bottom: 5px;">');
        });
        _wviewerswell.html(html.join('\n'));
        _wviewerswell.removeClass('hidden');
    });

    _jwcomponents.on('change', function () {
        var selected = $(this).find("option:selected").val();
        findFlow(selected);
    });

    $("#component-form").submit(function () {
        var ctype = $('#ctype').val();
        if (!$('#croot').is(":checked")) {
            if (_cparent.val() == undefined || _cparent.val() == '') {
                _jcformwrapper.nanoScroller({scrollTop: 0});
                $('button[data-id=cparent]').focus();
                return false;
            }
        }
        if (ctype == undefined || ctype == '') {
            _jcformwrapper.nanoScroller({scrollTop: 0});
            $('button[data-id=ctype]').focus();
            return false;
        }
        $('#usercode').val(_aceeditor.getSession().getValue());
        return true;
    });

    $("#combiner-form").submit(function () {
        var mflow = $('#mflow').val();
        var mtype = $('#mtype').val();
        if (mflow == undefined || mflow == '') {
            _jmformwrapper.nanoScroller({scrollTop: 0});
            $('button[data-id=mflow]').focus();
            return false;
        }
        if (mtype == undefined || mtype == '') {
            _jcformwrapper.nanoScroller({scrollTop: 0});
            $('button[data-id=mtype]').focus();
            return false;
        }
        $('#combinercode').val(_acecombiner.getSession().getValue());
        return true;
    });


    $("#workflow-form").submit(function () {
        if (_jwcomponents.val() == undefined || _jwcomponents.val() == '') {
            _jwformwrapper.nanoScroller({scrollTop: 0});
            $('button[data-id=wcomponents]').focus();
            return false;
        }
        return true;
    });

    $.blockUI.defaults.growlCSS.top = '70px';
    $.blockUI.defaults.growlCSS.opacity = '1';

    var $componentStatus = $('#component-status');
    if ($componentStatus.length > 0) {
        $.growlUI($componentStatus.data('heading'), $componentStatus.data('message'));
    }

    var $workflowStatus = $('#workflow-status');
    if ($workflowStatus.length > 0) {
        $.growlUI($workflowStatus.data('heading'), $workflowStatus.data('message'));
    }

    var $combinerStatus = $('#combiner-status');
    if ($combinerStatus.length > 0) {
        $.growlUI($combinerStatus.data('heading'), $combinerStatus.data('message'));
    }
    initializeSelectpickers(); //Important to initialize all the select pickers before calling them.
    var opentab = $('#open-tab').val();
    if (opentab == 'component') {
        var opencomp = $('#open-component');
        _opencomponent = opencomp.data('componentid');
        $('#cid-' + _opencomponent).click();
        editComponent();
    } else if (opentab == 'workflow') {
        var openwf = $('#open-workflow');
        _openworkflow = openwf.data('workflowid');
        $('#wfid-' + _openworkflow).click();
        editWorkflow();
    } else if (opentab == 'combiner') {
        var opencomb = $('#open-combiner');
        _opencombiner = opencomb.data('combinerid');
        $('#mid-' + _opencombiner).click();
        editCombiner();
    }
    initializeTabChange('#' + opentab);

    _jworkflowwrapper.on("update", function (event, val) {
        if (val.direction != 'up') {
            showTimeline();
        }
    });


    $('#schedule-repeat').on('change', function () {
        var selected = $(this).find("option:selected").val();
        if (selected == 'custom') {
            $('#schedule-custom-count').removeAttr('disabled');
            var $custom = $('#schedule-custom-repeat');
            $custom.removeAttr('disabled').selectpicker('refresh');
            if ($custom.val() == 'week') {
                $('#schedule-week-repeat').removeAttr('disabled').selectpicker('refresh');
            }
        } else {
            $('#schedule-custom-count').attr('disabled', 'true');
            $('#schedule-custom-repeat').attr('disabled', 'true').selectpicker('refresh');
            $('#schedule-week-repeat').attr('disabled', 'true').selectpicker('refresh');
            if (selected == 'none')
                $('#schedule-end').attr('disabled', 'true').selectpicker('refresh');
            else
                $('#schedule-end').removeAttr('disabled').selectpicker('refresh');
        }
    });

    $('#schedule-custom-repeat').on('change', function () {
        var selected = $(this).find("option:selected").val();
        if (selected == 'week') {
            $('#schedule-week-repeat').removeAttr('disabled').selectpicker('refresh');
        } else {
            $('#schedule-week-repeat').attr('disabled', 'true').selectpicker('refresh');
        }
    });

    $('#schedule-end').on('change', function () {
        var selected = $(this).find("option:selected").val();
        if (selected == 'date') {
            $('input[name=schedule-until]').removeAttr('disabled');
            $('#schedule-count').addClass('hidden');
            $('#schedule-until').removeClass('hidden');
        } else if (selected == 'count') {
            $('#schedule-count').removeClass('hidden').removeAttr('disabled');
            $('#schedule-until').addClass('hidden');
        } else {
            $('#schedule-count').attr('disabled', 'true');
            $('input[name=schedule-until]').attr('disabled', 'true');
        }
    });

    var $confirmDelete = $('#confirm-delete');
    $confirmDelete.on('show.bs.modal', function (e) {
        var data = $(e.relatedTarget).data();
        if (data.formTitle == 'component')
            $('#warn-message', this).text("Deleting this component will delete all the components to which this component" +
                " is a parent, workflows associated with this and those components," +
                " combiners associated with those workflows" +
                " and their dependencies, and so on until no more dependencies are left." +
                " Do you really want to continue?");
        else if (data.formTitle == 'workflow')
            $('#warn-message', this).text("Deleting this workflow will delete all the combiners to which this workflow" +
                " is a source, components to which those combiners are parents, workflows associated with those components" +
                " and their dependencies, and so on until no more dependencies are left." +
                " Do you really want to continue?");
        else
            $('#warn-message', this).text("Deleting this combiner will delete all the components to which this combiner" +
                " is a parent, workflows associated with those components, combiners associated with those workflows" +
                " and their dependencies, and so on until no more dependencies are left." +
                " Do you really want to continue?");
        $('.btn-ok', this).data('formTitle', data.formTitle);
    });
    $confirmDelete.on('click', '.btn-ok', function (e) {
        var $modalDiv = $(e.delegateTarget);
        var formTitle = $(this).data('formTitle');
        $modalDiv.modal('hide');
        if (formTitle == 'component')
            $('#hidden-delete-component').click();
        else if (formTitle == 'workflow')
            $('#hidden-delete-workflow').click();
        else
            $('#hidden-delete-combiner').click();
    });

    initializeScrollOnHover($('#w-schedule'));
    var $wtables = $('#wtables');
    var $csource = $('#constraint-source');
    var $ctable = $('#constraint-table');
    var $wfeature = $('#w-feature-label');
    var $wautorun = $('#workflow-auto-run-div');
    var $where = $('#where-clause');

    $csource.on('change', function () {
        var source = $(this).val();
        var url = source == "bigquery" ? "/bigquery/?name=tables" : "/galileo/?route=filesystem&q=names";
        showOverlay();
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            timeout: 60000,
            success: function (response) {
                var html = [];
                if (source == "bigquery") {
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
                } else {
                    if (response.what == 'filesystem#names') {
                        var filesystems = response.result;
                        $(filesystems).each(function (index, filesystem) {
                            html.push('<option value="' + filesystem.name + '" data-earliest="' + filesystem.earliestTime +
                                '" data-latest="' + filesystem.latestTime + '">' + filesystem.name + '</option>');
                        });
                    } else if (response.what == 'error') {
                        showErrorGrowl('Something went wrong!', response.result + '. If the issue persists, please seek support.');
                    }
                }
                html = html.join('');
                $ctable.prop('title', source == 'galileo' ? 'Choose a filesystem' : 'Choose a table');
                $ctable.html(html);
                initializeScrollOnHover($ctable);
                hideOverlay();
            },
            error: function (jqXHR, textStatus) {
                hideOverlay();
                if (textStatus === 'timeout') {
                    showErrorGrowl('Server timed out!',
                        'Try refreshing the browser. If the issue persists, please seek support.');
                } else {
                    showErrorGrowl('Something went wrong!', 'If the issue persists, please seek support.');
                }
            }
        });
    });


    $('#wauto').change(function () {
        if ($(this).is(':checked')) {
            $wautorun.find('input').removeAttr('disabled');
            var runtype = $('input[name="w-autorun-type"]:checked').val();
            chooseAutorunType(runtype);
            $wautorun.find('select').each(function () {
                $(this).removeAttr('disabled');
                initializeScrollOnHover($(this));
            });
            if (!_bqtablesInitialized) {
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
                        $wtables.html(html);
                        $ctable.html(html);
                        initializeScrollOnHover($wtables);
                        initializeScrollOnHover($ctable);
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
                _bqtablesInitialized = true;
            }
        } else {
            $wautorun.find('input').attr('disabled', true);
            $wautorun.find('select').attr('disabled', true).selectpicker('refresh');
        }
        $where.attr('disabled', true);
    }).trigger('change');


    $wtables.on('change', function () {
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
                $wfeature.html(html.join(''));
                initializeScrollOnHover($wfeature);
                hideOverlay();
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
                var $wconstraint = $('#w-auto-constraint');
                $wconstraint.html(html);
                initializeScrollOnHover($wconstraint);
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

    var $cfeature = $('#feature-label');
    $ctable.on('change', function () {
        var source = $csource.val();
        var table = $(this).val();
        var url = (source == "galileo" ? "/galileo/?route=features&fsname=" + table : "/bigquery/?name=features&table=" + table);
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            timeout: 60000,
            success: function (response) {
                var html = [];
                if (source == "bigquery") {
                    $.each(response.result, function (index, feature) {
                        for (var name in feature) {
                            html.push("<option data-type='" + feature[name] + "' value='" + name + "'>" + name + "</option>");
                        }
                    });
                } else {
                    var dataTypes = {"INTEGER": 1, "LONG": 2, "FLOAT": 3, "DOUBLE": 4, "STRING": 9};
                    $.each(response.result[0][table], function (index, feature) {
                        if (!(feature.name.startsWith("x__") && feature.name.endsWith("__x")))
                            html.push("<option data-type='" + dataTypes[feature.type] + "' value='" + feature.name + "'>" +
                                "" + feature.name + "</option>");
                    });
                }
                $cfeature.html(html.join(''));
                initializeScrollOnHover($cfeature);
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
            url: "/elements/?name=constraint&source=" + source + "&table=" + table,
            type: 'GET',
            dataType: 'json',
            timeout: 10000,
            success: function (response) {
                var html = [];
                var $conditionListview = $('#condition-listview');
                $conditionListview.html('');
                $.each(response.result, function (index, constraint) {
                    html.push("<option value='" + constraint.id + "'>" + constraint.name + "</option>");
                    var newdiv = "<div id='condid-" + constraint.id + "' data-id='" + constraint.id + "' " +
                        "class='y-listitem' onclick='showConstraint(this)'>" +
                        "<span style='font-weight: 400'>" + constraint.name + "</span><br>" +
                        "<span style='font-size: 11px; font-weight: 100'>" + constraint.time + "</span>" +
                        "<div style='font-size: 14px; font-weight: 300; margin-top: 10px;'" +
                        "id='expression-" + constraint.id + "' class='collapse'> Table - " + constraint.table +
                        "<br/> Source - " + constraint.source +
                        "<br/> Expression - " + constraint.expression + "</div></div>";
                    $conditionListview.append(newdiv);
                });
                html = html.join('');
                var $cleft = $('#constraint-left');
                var $cright = $('#constraint-right');
                $cleft.html(html);
                $cright.html(html);
                initializeScrollOnHover($cleft);
                initializeScrollOnHover($cright);
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

    $wfeature.on('change', function () {
        var table = $wtables.val();
        var feature = $(this).val();
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
                var $wfvalue = $('#w-feature-value');
                $wfvalue.typeahead('destroy');
                $wfvalue.typeahead({
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

    $cfeature.on('change', function () {
        var source = $csource.val();
        var table = $ctable.val();
        var feature = $(this).val();
        if (source == "bigquery") {
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
                    var $bqvalue = $('#feature-value');
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
        }

    });

    $('#constraint-form').submit(function () {
        var $csource = $('#constraint-source');
        var $ctable = $('#constraint-table');
        var ctype = $('input[name="condition-type"]:checked').val();
        var $cname = $('#constraint-name');
        var $flabel = $('#feature-label');
        var $fval = $('#feature-value');
        var $cleft = $('#constraint-left');
        var $cright = $('#constraint-right');
        if ($ctable.val() == undefined || $ctable.val() == '') {
            $('button[data-id=constraint-table]').focus();
            return false;
        }
        if (ctype == 'simple') {
            if ($flabel.val() == undefined || $flabel.val() == '') {
                $('button[data-id=feature-label]').focus();
                return false;
            }
            if ($fval.val().trim() == '') {
                $fval.val('').focus();
                return false;
            }
            $('#feature-type').val($flabel.find('option[value=' + $flabel.val() + ']').data('type'));
        } else {
            if ($cleft.val() == undefined || $cleft.val() == '') {
                $('button[data-id=constraint-left]').focus();
                return false;
            }
            if ($cright.val() == undefined || $cright.val() == '') {
                $('button[data-id=constraint-right]').focus();
                return false;
            }
        }
        if ($cname.val().trim() == '') {
            $cname.val('').focus();
            return false;
        }
        $.post($(this).attr('action'), $(this).serialize(), function (response) {
            if (response.result == "error") {
                $('#constraint-alert-holder').show();
                $("#constraint-alert-message").text(response.message);
            } else {
                $('#constraint-alert-holder').hide();
                var constraint = response.message;
                var newdiv = "<div id='condid-" + constraint.id + "' data-id='" + constraint.id + "' " +
                    "class='y-listitem' onclick='showConstraint(this)'>" +
                    "<span style='font-weight: 400'>" + constraint.name + "</span><br>" +
                    "<span style='font-size: 11px; font-weight: 100'>" + constraint.time + "</span>" +
                    "<div style='font-size: 14px; font-weight: 300; margin-top: 10px;'" +
                    "id='expression-" + constraint.id + "' class='collapse'>Table - " + constraint.table +
                    "<br/> Source - " + constraint.source +
                    "<br/> Expression - " + constraint.expression + "</div></div>";
                $('#condition-listview').prepend(newdiv);
                _jcondlistwrapper.nanoScroller({destroy: true}); //for destroy nano
                _jcondlistwrapper.nanoScroller({sliderClass: 'yellow-nano-slider'}); //for init nanoScroller (reinit)
                $("#constraint-name").val("");
                $flabel.val("").selectpicker('refresh');
                $fval.val("");
                $cleft.prepend("<option value='" + constraint.id + "'>" +
                    constraint.name + "</option>").val("").selectpicker('refresh');
                $cright.prepend("<option value='" + constraint.id + "'>" +
                    constraint.name + "</option>").val("").selectpicker('refresh');
            }
        }).fail(function (response) {
            $('#constraint-alert-holder').show();
            $("#constraint-alert-message").text(response.message);
        });
        return false; // prevent default action
    });

    $('#schedule-form').submit(function () {
        var $startInput = $('#schedule-start-input');
        var $repeat = $('#schedule-repeat');
        var $customRepeat = $('#schedule-custom-repeat');
        var $customCount = $('#schedule-custom-count');
        var $weekRepeat = $('#schedule-week-repeat');
        var $end = $('#schedule-end');
        var $untilInput = $('#schedule-until-input');
        var $count = $('#schedule-count');
        var $name = $('#schedule-name');
        if ($startInput.val() == undefined || $startInput.val() == '') {
            $('#schedule-start').data("DateTimePicker").show();
            return false;
        }
        if ($repeat.val() == undefined || $repeat.val() == '') {
            $('button[data-id=schedule-repeat]').focus();
            return false;
        }
        if ($repeat.val() == 'custom' && $customCount.val().trim() == '') {
            $customCount.val('').focus();
            return false;
        }
        if ($repeat.val() == 'custom' && $customRepeat.val() == 'week' &&
            ($weekRepeat.val() == '' || $weekRepeat.val() == undefined)) {
            $('button[data-id=schedule-week-repeat]').focus();
            return false;
        }
        if ($repeat.val() != "none") {
            if ($end.val() == undefined || $end.val() == '') {
                $('button[data-id=schedule-end]').focus();
                return false;
            }
            if ($end.val() == 'date' && $untilInput.val() == '') {
                $('#schedule-until').data('DateTimePicker').show();
                return false;
            }
            if ($end.val() == 'count' && $count.val().trim() == '') {
                $count.val('').focus();
                return false;
            }
        }
        if ($name.val().trim() == '') {
            $name.val('').focus();
            return false;
        }
        $.post($(this).attr('action'), $(this).serialize(), function (response) {
            if (response.result == "error") {
                $('#schedule-alert-holder').show();
                $("#schedule-alert-message").text(response.message);
            } else {
                $('#schedule-alert-holder').hide();
                var schedule = response.message;
                var newdiv = "<div id='sid-" + schedule.id + "' data-id='" + schedule.id + "' " +
                    "class='b-listitem' onclick='showSchedule(this)'>" +
                    "<span style='font-weight: 400'>" + schedule.name + "</span><br>" +
                    "<span style='font-size: 11px; font-weight: 100'>" + schedule.time + "</span>" +
                    "<div style='font-size: 14px; font-weight: 300; margin-top: 10px;'" +
                    "id='schedule-" + schedule.id + "' class='collapse'>" + schedule.details + "</div></div>";
                $('#schedule-listview').prepend(newdiv);
                _jschdlistwrapper.nanoScroller({destroy: true}); //for destroy nano
                _jschdlistwrapper.nanoScroller(); //for init nanoScroller (reinit)
                $("#schedule-name").val("");
                $startInput.val('');
                $repeat.selectpicker('val', '').trigger('change');
                $customCount.val('');
                $customRepeat.selectpicker('val', 'day');
                $weekRepeat.selectpicker('val', '');
                $end.selectpicker('val', '').trigger('change');
                $count.val('');
                $untilInput.val('');
                $name.val('');
            }
        }).fail(function (response) {
            $('#schedule-alert-holder').show();
            $("#schedule-alert-message").text(response.message);
        });
        return false; // prevent default action
    });

    $('#ft-import-form').submit(function () {
        $('#fusion-table-modal').modal('hide');
        showOverlay();
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: $(this).serialize(),
            dataType: "json",
            success: function (response) {
                hideOverlay();
                if (response.result == "success")
                    window.location.href = "/workspace";
                else{
                    showErrorGrowl("Something went wrong!", response.message);
                }
            }
        }).fail(function (response) {
            hideOverlay();
            showErrorGrowl("Something went wrong!",
                "If the issue persists, please seek support.\n" + JSON.stringify(response));
        });
        return false;
    });
});

function initializeSelectpickers() {
    $('.selectpicker').selectpicker('refresh');
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


function initializeTabChange(target) {
    var $start, $until;
    if (target == '#other') {
        if (!_bqtablesInitialized) {
            var $wtables = $('#wtables');
            var $ctable = $("#constraint-table");
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
                    $wtables.html(html);
                    $ctable.html(html);
                    initializeScrollOnHover($wtables);
                    initializeScrollOnHover($ctable);
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
            _bqtablesInitialized = true;
        }
        initMap();
        $start = $('#schedule-start');
        $until = $('#schedule-until');
    } else if (target == '#combiner') {
        $start = $('#mstart-div');
        $until = $('#mend-div');
    }
    if ($start != undefined && $until != undefined) {
        $start.datetimepicker({
            useCurrent: false,
            ignoreReadonly: true,
            showTodayButton: true,
            showClear: true
        });
        $until.datetimepicker({
            useCurrent: false, //Important
            ignoreReadonly: true,
            showTodayButton: true,
            showClear: true
        });
        $start.on("dp.change", function (e) {
            $until.data("DateTimePicker").minDate(e.date);
        });
        $until.on("dp.change", function (e) {
            $start.data("DateTimePicker").maxDate(e.date);
        });
    }
}

function showTimeline() {
    $('.cd-timeline-block').each(function () {
        if ($(this).offset().top <= _jwflowheight &&
            $(this).find('.cd-timeline-img').hasClass('is-hidden')) {
            $(this).find('.cd-timeline-img, .cd-timeline-content')
                .removeClass('is-hidden').addClass('bounce-in');
        }
    });
}

function buildFlow(result) {
    //result must be an array having id values of the components and combiners
    var flowhtml = [];
    $.each(result, function (index, el) {
        el = el.trim();
        var element = $("#" + el);
        var html = '<div class="cd-timeline-block">';
        var component = el.startsWith('cid') ? true : false;
        if (index + 1 == result.length) {
            //definitely a component
            $('#wfoutput').val(element.data('output'));
            html = html + '<div class="cd-timeline-img cd-movie is-hidden">';
        } else {
            html = html + (component ? '<div class="cd-timeline-img cd-picture is-hidden">' :
                    '<div class="cd-timeline-img cd-location is-hidden">');
        }
        html = html + '<span>' + (index + 1) + '</span>' +
            '</div>' +
            '<div class="cd-timeline-content is-hidden">' +
            '<h2>' + element.data(component ? 'componentname' : 'combinername') + '</h2>' +
            '<p>' + element.data('description').replace(new RegExp('\r?\n', 'g'), '<br/>') + '</p>' +
            '<div class="collapse" id="collapse-' + el + '">' +
            '<label class="timeline-heading">Output Description</label>' +
            '<p>' + element.data('output').replace(new RegExp('\r?\n', 'g'), '<br/>') + '</p> ' +
            '</div>' +
            '<a href="#collapse-' + el + '" ' +
            'data-toggle="collapse" aria-expanded="false" ' +
            'aria-controls="collapse-' + el + '" ' +
            'class="cd-read-more btn">Show more</a>' +
            '<span class="cd-date">' + element.data('type') + '</span>' +
            '</div>' +
            '</div>';
        flowhtml.push(html);
    });
    _flowplaceholder.html('<p style="text-align: center;width: 150px; height: 40px;">' +
        'Choose a component to see the flow here' +
        '</p>');
    if (flowhtml.length == 0) {
        _flowplaceholder.html('<p style="text-align: center;width: 150px; height: 40px;">' +
            'No flow found for the chosen component' +
            '</p>');
        $('#wfoutput').val('');
        _flowplaceholder.removeClass('hidden');
        _cdtimeline.addClass('hidden');
    } else {
        _flowplaceholder.addClass('hidden');
        _cdtimeline.removeClass('hidden');
        _cdtimeline.html(flowhtml.join('\n'));
        $('.collapse').on('shown.bs.collapse', function () {
            $(this).next('a').html('Show less');
        });
        $('.collapse').on('hidden.bs.collapse', function () {
            $(this).next('a').html('Show more');
        });
        showTimeline();
    }
    _jwtimeline.nanoScroller({destroy: true})
    _jwtimeline.nanoScroller();
}

function findFlow(id) {
    $.ajax({
        url: "/getchain/?compid=" + id,
        type: 'GET',
        dataType: 'json',
        timeout: '15000',
        success: function (response) {
            if (response.result == 'error') {
                _flowplaceholder.html('<p style="text-align: center;width: 150px; height: 40px;">' +
                    'The flow contains a cycle and cannot be executed. Please revise and try again.' +
                    '</p>');
                $('#wfoutput').val('');
                _flowplaceholder.removeClass('hidden');
                _cdtimeline.addClass('hidden');
            } else {
                var result = response.result;
                result = result.substring(1, result.length - 1).split(",");
                buildFlow(result);
            }
        },
        error: function (jqXHR, textStatus) {
            showErrorGrowl('Something went wrong',
                'Unable to verify the flow. Please seek support if the issue persists.');
        }
    });
}

function resizeWrappers() {
    _jclistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jclistwrapper.nanoScroller(); //for init nanoScroller (reinit)
    _jcformwrapper.nanoScroller({destroy: true});
    var editorHeight = parseFloat(_jeditorwrapper.css('height'));
    editorHeight -= 38; //padding-top + padding-bottom + margin-top + margin-bottom of the wrapper and header
    _jeditor.css('height', editorHeight + 'px');
    _jcformwrapper.css('height', (editorHeight - 60) + 'px');
    _jcformwrapper.nanoScroller();

    _jwlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jwlistwrapper.nanoScroller(); //for init nanoScroller (reinit)
    _jwflowheight = parseFloat(_jworkflowwrapper.css('height'));
    _jwformwrapper.css('height', (_jwflowheight - 98) + 'px');
    _jwformwrapper.nanoScroller();
    _jwtimeline.nanoScroller({destroy: true})
    _jwtimeline.nanoScroller();

    _jmlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jmlistwrapper.nanoScroller(); //for init nanoScroller (reinit)
    editorHeight = parseFloat(_jmeditorwrapper.css('height'));
    editorHeight -= 38; //padding-top + padding-bottom + margin-top + margin-bottom of the wrapper and header
    _jmeditor.css('height', editorHeight + 'px');
    _jmformwrapper.css('height', (editorHeight - 60) + 'px');
    _jmformwrapper.nanoScroller();

    _jpolylistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jpolylistwrapper.nanoScroller({sliderClass: 'green-nano-slider'}); //for init nanoScroller (reinit)
    _jcondlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jcondlistwrapper.nanoScroller({sliderClass: 'yellow-nano-slider'}); //for init nanoScroller (reinit)
    _jschdlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jschdlistwrapper.nanoScroller({sliderClass: 'blue-nano-slider'}); //for init nanoScroller (reinit)
}

function showComponent(listitem) {
    if ($(listitem).data('executing')) return;

    $('#save-component').addClass('disabled').attr('disabled', 'true');
    $('#edit-component').removeClass('disabled').removeAttr('disabled');
    $('#component-title').text($(listitem).data('componentname'));
    $('#poutput').val('');
    if ($(listitem).data('componentid') != _opencomponent) {
        $('#component-alert-holder').alert("close");
        _opencomponent = undefined;
    }

    _cparentoptions.each(function () {
        $(this).removeAttr('disabled');
        if (this.value == $(listitem).data('componentid'))
            $(this).attr('disabled', 'true');
    });
    _cparent.selectpicker('refresh');
    _cparties.selectpicker('refresh');
    var $ctype = $('#ctype');

    if ($(listitem).data('componentid') == 0) {
        $('#component-edit-group').hide();
        $('#component-read-group').hide();
        $('#component-create-group').show();
        $('#cname').removeAttr('disabled').val('');
        _cparent.removeAttr('disabled').val('');
        _cparties.removeAttr('disabled').val('');
        $('#coutput').removeAttr('disabled').val('');
        $('#cdesc').removeAttr('disabled').val('');
        $ctype.removeAttr('disabled').val('');
        _cref.addClass('hidden');
        _cparentwell.addClass('hidden');
        _cpartieswell.addClass('hidden');
        $('#cvis').removeAttr("disabled").prop('checked', false).trigger('change').parent().css('cursor', 'pointer');
        $('#croot').removeAttr("disabled").prop('checked', false).trigger('change').parent().css('cursor', 'pointer');
        $('#cparties-div').addClass('hidden');
        $('#component-id').val('0');
        _aceeditor.setReadOnly(false);
        _aceeditor.getSession().setValue(_editormessage);
    } else {
        $.get("/usercode/?componentid=" + $(listitem).data('componentid'), function (response, status) {
            _aceeditor.getSession().setValue(response);
        }, "text");
        _aceeditor.setReadOnly(true);
        $('#component-create-group').hide();
        if ($(listitem).data('readonly')) {
            $('#component-read-group').show();
            $('#component-edit-group').hide();
        } else {
            $('#component-edit-group').show();
            $('#component-read-group').hide();
        }
        $('#cname').attr('disabled', true).val($(listitem).data('componentname'));
        $('#cdesc').attr('disabled', true).val($(listitem).data('description'));
        _cparent.attr('disabled', true);
        _cparties.attr('disabled', true);
        $('#coutput').attr('disabled', true).val($(listitem).data('output'));
        $('#component-id').val($(listitem).data('componentid'));
        _cref.removeClass('hidden');
        $('#cvis').prop('checked', $(listitem).data('visualizer') == "True").trigger('change')
            .attr("disabled", true).parent().css('cursor', 'not-allowed');
        $('#croot').prop('checked', $(listitem).data('root') == "True").trigger('change')
            .attr("disabled", true).parent().css('cursor', 'not-allowed');
        _cref.html('component-' + $(listitem).data('componentid'));
        _cref.attr('data-clipboard-text', 'component-' + $(listitem).data('componentid'));
        $ctype.attr('disabled', true).selectpicker('refresh');
        $ctype.val($(listitem).data('typeid'));
        var parents = $(listitem).data('parentid').toString();
        parents = (parents.trim().length != 0) ? parents.split(",").map(function (parent_id) {
            return 'component-' + parent_id.trim();
        }) : [];
        var combiners = $(listitem).data('combinerid').toString();
        combiners = (combiners.trim().length != 0) ? combiners.split(",").map(function (combiner_id) {
            return 'combiner-' + combiner_id.trim();
        }) : [];
        parents = parents.concat(combiners);
        _cparent.selectpicker('val', parents);
        _cparent.trigger('change');

        var parties = $(listitem).data('parties').toString();
        if (parties.trim().length != 0) {
            parties = parties.split(",");
            _cparties.selectpicker('val', parties);
            _cparties.trigger('change');
        } else {
            _cparties.selectpicker('val', '');
            _cpartieswell.addClass('hidden');
        }
    }

    _clipboard.destroy();
    _clipboard = new Clipboard(document.querySelectorAll('aside'));

    _cparent.selectpicker('refresh');
    _cparties.selectpicker('refresh');
    $ctype.selectpicker('refresh');
    if (_lastcomponent != undefined) {
        $(_lastcomponent).css('background-color', '');
        $(_lastcomponent).css('color', '');
        $(_lastcomponent).removeData('executing');
        $(_lastcomponent).css('cursor', '');
    }
    _lastcomponent = listitem;
    $(listitem).css('background-color', '#eb9316');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    $(listitem).css('cursor', 'default');
}


function showCombiner(listitem) {
    if ($(listitem).data('executing')) return;

    $('#save-combiner').addClass('disabled').attr('disabled', 'true');
    $('#edit-combiner').removeClass('disabled').removeAttr('disabled');
    $('#combiner-title').text($(listitem).data('combinername'));

    if ($(listitem).data('combinerid') != _opencombiner) {
        $('#combiner-alert-holder').alert("close");
        _opencombiner = undefined;
    }
    var $mtype = $('#mtype');
    _mparties.selectpicker('refresh');
    if ($(listitem).data('combinerid') == 0) {
        $('#combiner-edit-group').hide();
        $('#combiner-read-group').hide();
        $('#combiner-create-group').show();
        $('#mname').removeAttr('disabled').val('');
        $('#mdesc').removeAttr('disabled').val('');
        $('#mflow').removeAttr('disabled').val('').selectpicker('refresh');
        $mtype.removeAttr('disabled').val('5').selectpicker('refresh');
        $('#moutput').removeAttr('disabled').val('');
        $('#mstart').removeAttr('disabled').val('');
        $('#mend').removeAttr('disabled').val('');
        $('#combiner-id').val('0');
        _mref.addClass('hidden');
        _acecombiner.setReadOnly(false);
        _acecombiner.getSession().setValue(_editormessage);
        _mparties.removeAttr('disabled').val('');
        _mpartieswell.addClass('hidden');
        $('#mvis').removeAttr("disabled").prop('checked', false).trigger('change').parent().css('cursor', 'pointer');
        $('#mparties-div').addClass('hidden');
    } else {
        $.get("/usercode/?combinerid=" + $(listitem).data('combinerid'), function (response, status) {
            _acecombiner.getSession().setValue(response);
        }, "text");
        _acecombiner.setReadOnly(true);
        $('#combiner-create-group').hide();
        if ($(listitem).data('readonly')) {
            $('#combiner-read-group').show();
            $('#combiner-edit-group').hide();
        } else {
            $('#combiner-edit-group').show();
            $('#combiner-read-group').hide();
        }
        $('#mname').attr('disabled', true).val($(listitem).data('combinername'));
        $('#mdesc').attr('disabled', true).val($(listitem).data('description'));
        $('#combiner-id').val($(listitem).data('combinerid'));
        $('#mflow').selectpicker('val', $(listitem).data('flowid')).attr('disabled', true).selectpicker('refresh');
        $mtype.attr('disabled', true).selectpicker('refresh');
        $mtype.val($(listitem).data('typeid'));
        $('#moutput').attr('disabled', true).val($(listitem).data('output'));
        $('#mstart').attr('disabled', true).val($(listitem).data('start'));
        $('#mend').attr('disabled', true).val($(listitem).data('end'));
        _mparties.attr('disabled', true);
        _mref.removeClass('hidden');
        _mref.html('combiner-' + $(listitem).data('combinerid'));
        _mref.attr('data-clipboard-text', 'combiner-' + $(listitem).data('combinerid'));
        $('#mvis').prop('checked', $(listitem).data('visualizer') == "True").trigger('change')
            .attr("disabled", true).parent().css('cursor', 'not-allowed');
        var parties = $(listitem).data('parties').toString();
        if (parties.trim().length != 0) {
            parties = parties.split(",");
            _mparties.selectpicker('val', parties);
            _mparties.trigger('change');
        } else {
            _mparties.selectpicker('val', '');
            _mpartieswell.addClass('hidden');
        }
    }

    _clipboard.destroy();
    _clipboard = new Clipboard(document.querySelectorAll('aside'));
    $mtype.selectpicker('refresh');
    _mparties.selectpicker('refresh');
    if (_lastcombiner != undefined) {
        $(_lastcombiner).css('background-color', '');
        $(_lastcombiner).css('color', '');
        $(_lastcombiner).removeData('executing');
        $(_lastcombiner).css('cursor', '');
    }
    _lastcombiner = listitem;
    $(listitem).css('background-color', '#eb9316');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    $(listitem).css('cursor', 'default');
}


function showWorkflow(listitem) {
    if ($(listitem).data('executing')) return;

    $('#save-workflow').addClass('disabled').attr('disabled', 'true');
    $('#edit-workflow').removeClass('disabled').removeAttr('disabled');
    $('#workflow-title').text($(listitem).data('workflowname'));

    if ($(listitem).data('workflowid') != _openworkflow) {
        $('#workflow-alert-holder').alert("close");
        _openworkflow = undefined;
    }
    _wviewers.selectpicker('refresh');
    if ($(listitem).data('workflowid') == 0) {
        $('#workflow-edit-group').hide();
        $('#workflow-read-group').hide();
        $('#workflow-create-group').show();
        $('#wfname').removeAttr('disabled').val('');
        $('#wfdesc').removeAttr('disabled').val('');
        _jwcomponents.removeAttr('disabled');
        $('#wfoutput').val('');
        _jwcomponents.val('');
        $('#workflow-id').val('0');
        _jwcomponents.selectpicker('refresh');
        _flowplaceholder.html('<p style="text-align: center;width: 150px; height: 40px;">' +
            'Choose a component to see the flow here' +
            '</p>');
        _flowplaceholder.removeClass('hidden');
        _cdtimeline.addClass('hidden');
        _wviewers.removeAttr('disabled').val('');
        _wviewerswell.addClass('hidden');
        $('#wshare').removeAttr("disabled").prop('checked', false).trigger('change').parent().css('cursor', 'pointer');
        $('#wviewers-div').addClass('hidden');
    } else {
        $('#workflow-create-group').hide();
        if ($(listitem).data('readonly')) {
            $('#workflow-read-group').show();
            $('#workflow-edit-group').hide();
        } else {
            $('#workflow-edit-group').show();
            $('#workflow-read-group').hide();
        }
        $('#wfname').attr('disabled', true).val($(listitem).data('workflowname'));
        $('#wfdesc').attr('disabled', true).val($(listitem).data('description'));
        $('#workflow-id').val($(listitem).data('workflowid'));
        _jwcomponents.selectpicker('refresh'); //don't remove this line
        _jwcomponents.val($(listitem).data('componentid'));
        //_jwcomponents.trigger('change');
        _jwcomponents.attr('disabled', true);
        _jwcomponents.selectpicker('refresh');
        var chain = $(listitem).data('chain');
        chain = chain.substring(1, chain.length - 1).split(",");
        buildFlow(chain);
        _wviewers.attr('disabled', true);
        $('#wshare').prop('checked', $(listitem).data('sharing') == "True").trigger('change')
            .attr("disabled", true).parent().css('cursor', 'not-allowed');
        var viewers = $(listitem).data('viewers').toString();
        if (viewers.trim().length != 0) {
            viewers = viewers.split(",");
            _wviewers.selectpicker('val', viewers);
            _wviewers.trigger('change');
        } else {
            _wviewers.selectpicker('val', '');
            _wviewerswell.addClass('hidden');
        }
    }
    _wviewers.selectpicker('refresh');
    if (_lastworkflow != undefined) {
        $(_lastworkflow).css('background-color', '');
        $(_lastworkflow).css('color', '');
        $(_lastworkflow).removeData('executing');
        $(_lastworkflow).css('cursor', '');
    }
    _lastworkflow = listitem;
    $(listitem).css('background-color', '#eb9316');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    $(listitem).css('cursor', 'default');
}

function showConstraint(listitem) {
    if ($(listitem).data('executing')) {
        $("#expression-" + $(_lastCondition).data("id")).collapse('toggle');
        return;
    }
    $("#expression-" + $(listitem).data("id")).collapse('show');
    if (_lastCondition != undefined) {
        $(_lastCondition).css('background-color', '');
        $(_lastCondition).css('color', '');
        $(_lastCondition).removeData('executing');
    }
    _lastCondition = listitem;
    $(listitem).css('background-color', '#F9A825');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    _jcondlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jcondlistwrapper.nanoScroller({sliderClass: 'yellow-nano-slider'}); //for init nanoScroller (reinit)
}

function showSchedule(listitem) {
    if ($(listitem).data('executing')) {
        $("#schedule-" + $(_lastSchedule).data("id")).collapse('toggle');
        return;
    }
    $("#schedule-" + $(listitem).data("id")).collapse('show');
    if (_lastSchedule != undefined) {
        $(_lastSchedule).css('background-color', '');
        $(_lastSchedule).css('color', '');
        $(_lastSchedule).removeData('executing');
    }
    _lastSchedule = listitem;
    $(listitem).css('background-color', '#039BE5');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    _jschdlistwrapper.nanoScroller({destroy: true}); //for destroy nano
    _jschdlistwrapper.nanoScroller({sliderClass: 'green-nano-slider'}); //for init nanoScroller (reinit)
}

function editComponent() {
    $('#cname').removeAttr('disabled');
    $('#cdesc').removeAttr('disabled');
    $('#ctype').removeAttr('disabled').selectpicker('refresh');
    $('#coutput').removeAttr('disabled');
    $('#cvis').removeAttr('disabled').parent().css('cursor', 'pointer');
    $('#cparties').removeAttr('disabled').selectpicker('refresh');
    $('#save-component').removeAttr('disabled').removeClass('disabled');
    $('#edit-component').addClass('disabled').attr('disabled', 'true');
    _aceeditor.setReadOnly(false);
}

function editWorkflow() {
    $('#wfname').removeAttr('disabled');
    $('#wfdesc').removeAttr('disabled');
    $('#save-workflow').removeAttr('disabled').removeClass('disabled');
    $('#edit-workflow').addClass('disabled').attr('disabled', 'true');
    $('#wshare').removeAttr('disabled').parent().css('cursor', 'pointer');
    $('#wviewers').removeAttr('disabled').selectpicker('refresh');
}

function editCombiner() {
    $('#mname').removeAttr('disabled');
    $('#mdesc').removeAttr('disabled');
    $('#mtype').removeAttr('disabled').selectpicker('refresh');
    $('#mflow').removeAttr('disabled').selectpicker('refresh');
    $('#moutput').removeAttr('disabled');
    $('#mstart').removeAttr('disabled');
    $('#mend').removeAttr('disabled');
    $('#mvis').removeAttr('disabled').parent().css('cursor', 'pointer');
    $('#mparties').removeAttr('disabled').selectpicker('refresh');
    $('#save-combiner').removeAttr('disabled').removeClass('disabled');
    $('#edit-combiner').attr('disabled', 'true').addClass('disabled');
    _acecombiner.setReadOnly(false);
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

function showOverlay() {
    $.blockUI({
        message: '<h4>Please wait...</h4>',
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

function hideOverlay() {
    $.unblockUI();
}

// called by the google maps api
function initMap() {
    //Enabling new cartography and themes
    google.maps.visualRefresh = true;
    //Setting starting options of map
    var mapOptions = {
        center: new google.maps.LatLng(40, -100),
        zoom: 4,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        panControl: false,
        zoomControl: false,
        scaleControl: false,
        streetViewControl: false,
        mapTypeControl: false
    };
    //Getting map DOM element
    var mapElement = $('#polygon-map')[0];
    map = new google.maps.Map(mapElement, mapOptions);
}

function showPolygon(listitem) {
    if ($(listitem).data('executing')) return;
    if (_lastPolygon != undefined) {
        $(_lastPolygon).css('background-color', '');
        $(_lastPolygon).css('color', '');
        $(_lastPolygon).removeData('executing');
        $(_lastPolygon).css('cursor', '');
    }
    _lastPolygon = listitem;
    $(listitem).css('background-color', '#009688');
    $(listitem).css('color', '#fff');
    $(listitem).data('executing', true);
    $(listitem).css('cursor', 'default');

    if (_drewPolygon != undefined)
        _drewPolygon.setMap(null);
    var paths = [];
    var bounds = new google.maps.LatLngBounds(); //bounding box of the polygon
    $.each($(listitem).data('polygon'), function (index, item) {
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
        fillOpacity: 0.0
    });
    _drewPolygon.setMap(map);
    //set map center to polygon center
    map.fitBounds(bounds);
}

function chooseConstraint(type) {
    if (type == 'simple') {
        $('#feature-label').removeAttr('disabled').selectpicker('refresh');
        $('#feature-op').removeAttr('disabled').selectpicker('refresh');
        $('#feature-value').removeAttr('disabled');
        $('#constraint-left').attr('disabled', 'true').selectpicker('refresh');
        $('#joint').attr('disabled', 'true').selectpicker('refresh');
        $('#constraint-right').attr('disabled', 'true').selectpicker('refresh');
    } else {
        $('#feature-label').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-op').attr('disabled', 'true').selectpicker('refresh');
        $('#feature-value').attr('disabled', 'true');
        $('#constraint-left').removeAttr('disabled').selectpicker('refresh');
        $('#joint').removeAttr('disabled').selectpicker('refresh');
        $('#constraint-right').removeAttr('disabled').selectpicker('refresh');
    }
}

function chooseAutorunType(runType) {
    if (runType == "for") {
        $('#w-feature-op').removeAttr('disabled').selectpicker('refresh');
        $('#w-feature-value').removeAttr('disabled');
    } else {
        $('#w-feature-op').attr('disabled', 'true').selectpicker('refresh');
        $('#w-feature-value').attr('disabled', 'true');
    }
}