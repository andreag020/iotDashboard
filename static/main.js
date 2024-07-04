$(document).ready(function () {
    // Initialize Socket.IO for real-time communication
    var socket = io();

    // Listen for the 'updated_devices' event from the server
    socket.on('updated_devices', function (data) {
        var deviceList = $("#device-list");
        // Clear the current device list
        deviceList.empty();
        // Iterate through the updated devices and append them to the list
        data.devices_db.forEach(function (device) {
            var checked = device.status[0].value ? 'checked' : '';
            var listItem = $("<li><input type='checkbox' class='device-toggle' data-device-id='" + device.id + "' " + checked + ">" + device.customName + " (" + device.id + ")</li>");
            deviceList.append(listItem);
        });
    });

    // Debounce function to limit the rate at which the sendUpdateRequest function is called
    function debounce(func, wait) {
        let timeout;
        return function () {
            const context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    // Function to send an update request to the server
    function sendUpdateRequest(deviceId, isActive) {
        $.post("/update_device_status", {device_id: deviceId, new_status: isActive}, function (data) {
            if (!data.success) {
                alert('Error updating device status. Please try again.');
                // Request updated device list if there's an error
                socket.emit('request_updated_devices');
            }
            // Re-enable the device toggle checkbox
            $('.device-toggle').prop('disabled', false);
        }).fail(function () {
            alert('Error sending update request. Please try again.');
            // Request updated device list if there's an error
            socket.emit('request_updated_devices');
            // Re-enable the device toggle checkbox
            $('.device-toggle').prop('disabled', false);
        });
    }

    // Create a debounced version of the sendUpdateRequest function
    const debouncedSendUpdateRequest = debounce(sendUpdateRequest, 300);

    // Event handler for changes to the device toggle checkboxes
    $(document).on('change', '.device-toggle', function () {
        var deviceId = $(this).data('device-id');
        var isActive = $(this).is(':checked');
        // Disable the checkbox while the update request is being sent
        $(this).prop('disabled', true);
        // Send the update request with a debounce
        debouncedSendUpdateRequest(deviceId, isActive);
    });

    // Emit an event to request the updated device list when the page loads
    socket.emit('request_updated_devices');
});
