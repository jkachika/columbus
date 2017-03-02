/**
 * Created by JohnsonCharles on 29-12-2016.
 */

var $instanceListWrapper;
var instanceCount;
var $selectedCount;
var $selectedCountText;
$(document).ready(function () {
    $instanceListWrapper = $('#instance-list-wrapper');
    resizeWrappers();
    $(window).resize(function () {
        resizeWrappers();
    });
    instanceCount = $('#instance_count').val();
    $selectedCount = $('#selected_count');
    $selectedCountText = $('#selected-count-text');
    $('#toggle-all').on('change', function () {
        if ($(this).prop('checked')) {
            $('input[type=checkbox]').prop('checked', true);
            $selectedCount.val(instanceCount);
            $selectedCountText.html(instanceCount);
        } else {
            $('input[type=checkbox]').prop('checked', false);
            $selectedCount.val(0);
            $selectedCountText.html(0);
        }
    });

    $('#instances-review-form').submit(function () {
        showOverlay();
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: $(this).serialize(),
            dataType: "json",
            success: function (response) {
                hideOverlay();
                if (response.result == "success")
                    window.location.href = "/dashboard/?q=pending";
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

function toggleSelection(checkbox) {
    var val = parseInt($selectedCount.val());
    if ($(checkbox).prop('checked')) {
        $selectedCountText.html(val + 1);
        $selectedCount.val(val + 1);
    } else {
        $selectedCountText.html(val - 1);
        $selectedCount.val(val - 1);
    }
}

function resizeWrappers() {
    $instanceListWrapper.nanoScroller({destroy: true}); //for destroy nano
    $instanceListWrapper.nanoScroller();
}

function increasePriority(instance_id) {
    var $input = $('#' + instance_id + '-priority');
    var priority = parseInt($input.val());
    if (priority >= 5)
        return false;
    priority += 1;
    $input.val(priority);
    $('#' + instance_id + '-priority-text').html($input.val());
    return false;
}

function decreasePriority(instance_id) {
    var $input = $('#' + instance_id + '-priority');
    var priority = parseInt($input.val());
    if (priority <= 1)
        return false;
    priority -= 1;
    $input.val(priority);
    $('#' + instance_id + '-priority-text').html($input.val());
    return false;
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