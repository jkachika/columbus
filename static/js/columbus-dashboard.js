/**
 * Created by JohnsonCharles on 02-01-2017.
 */

var $instanceListWrapper;
$(document).ready(function () {
    $instanceListWrapper = $('#instance-list-wrapper');
    resizeWrappers();
    $(window).resize(function () {
        resizeWrappers();
    });
    // Build the chart
    var baseChart = {
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie'
        },
        title: {
            text: ''
        },
        colors: [
            '#FDD835', '#795548', '#00E5FF', '#1DE9B6', '#E040FB'
        ],
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: false
                },
                showInLegend: true
            }
        },
        legend: {
            align: 'right',
            layout: 'vertical',
            verticalAlign: 'middle',
            width: 25,
            y: 5,
            x: -60,
            useHTML: true,
            labelFormatter: function () {
                return '<div style="text-align: left; width:130px;float:left;">' + this.name + '</div>' +
                    '<div style="width:40px; float:left;text-align:right;">' + this.y + '%</div>';
            }
        },
        series: [{
            name: 'Status',
            colorByPoint: true,
            data: [],
            size: '100%',
            innerSize: '50%',
            showInLegend: true
        }]
    };

    baseChart.series[0].data = workflowsData;
    var filteredFlows = workflowsData.filter(function (item) {
        return item[1] > 0;
    });
    Highcharts.chart('workflow-summary', baseChart);
    if (filteredFlows.length == 0) {
        baseChart.colors = ['#263238'];
        baseChart.series[0].data = [['None', 100]];
    }
    baseChart.series[0].data = usersData.filter(function (item) {
        return item.flows > 0
    });
    if (baseChart.series[0].data.length == 0) {
        baseChart.series[0].data = [['None', 100]];
        baseChart.colors = ['#263238'];
    } else {
        baseChart.legend.labelFormatter = function () {
            return '<div style="text-align: left; width:130px;float:left;">' + this.name + '</div>' +
                '<div style="width:40px; float:left;text-align:right;">' + this.flows + '</div>';
        };
        baseChart.colors = ['#8BC34A', '#FF4081', '#673AB7', '#2196F3', '#FF8F00'];
    }
    Highcharts.chart('user-summary', baseChart);
    //check if any errors are presented by the server
    var $errorHolder = $('#error-holder');
    if ($errorHolder.length != 0) {
        showErrorGrowl('Something went wrong!', $errorHolder.html());
        /*$.growl.error({
         title: 'Something went wrong!',
         message: $('#error-holder').html(),
         location: 'tc',
         delayOnHover: true,
         duration: 0
         });*/
    }
});


function resizeWrappers() {
    $instanceListWrapper.nanoScroller({destroy: true}); //for destroy nano
    $instanceListWrapper.nanoScroller();
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