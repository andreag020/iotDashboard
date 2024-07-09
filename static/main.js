$(document).ready(function () {
    var socket = io();

    socket.on('updated_devices', function (data) {
        var deviceList = $("#device-list");
        deviceList.empty();
        data.devices_db.forEach(function (device) {
            var checked = device.status[0].value ? 'checked' : '';
            var listItem = $("<div class='device-card'><div class='device-info'>" + device.customName + " (" + device.id + ")</div><label class='switch'><input type='checkbox' class='device-toggle' data-device-id='" + device.id + "' " + checked + "><span class='slider'></span></label></div>");
            deviceList.append(listItem);
        });
    });

    function debounce(func, wait) {
        let timeout;
        return function () {
            const context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    function sendUpdateRequest(deviceId, isActive) {
        $.post("/update_device_status", {device_id: deviceId, new_status: isActive}, function (data) {
            if (!data.success) {
                alert('Error updating device status. Please try again.');
                socket.emit('request_updated_devices');
            }
            $('.device-toggle').prop('disabled', false);
        }).fail(function () {
            alert('Error sending update request. Please try again.');
            socket.emit('request_updated_devices');
            $('.device-toggle').prop('disabled', false);
        });
    }

    const debouncedSendUpdateRequest = debounce(sendUpdateRequest, 300);

    $(document).on('change', '.device-toggle', function () {
        var deviceId = $(this).data('device-id');
        var isActive = $(this).is(':checked');
        $(this).prop('disabled', true);
        debouncedSendUpdateRequest(deviceId, isActive);
    });

    socket.emit('request_updated_devices');
});