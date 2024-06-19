$(document).ready(function () {
    function updateDeviceList() {
        if (isUpdating) return;
        $.get("/get_updated_devices", function (data) {
            var deviceList = $("#device-list");
            deviceList.empty();  // Vacía la lista de dispositivos
            data.devices_db.forEach(function (device) {
                var checked = device.status[0].value ? 'checked' : '';
                var listItem = $("<li><input type='checkbox' class='device-toggle' data-device-id='" + device.id + "' " + checked + ">" + device.name + " (" + device.id + ")</li>");
                deviceList.append(listItem);  // Agrega cada dispositivo a la lista
            });
        }).fail(function () {
            alert('Error al obtener la lista de dispositivos. Inténtalo de nuevo más tarde.');
        });
    }

    function sendUpdateRequest(deviceId, isActive) {
        isUpdating = true;  // Indica que se está enviando una solicitud POST
        $.post("/update_device_status", {device_id: deviceId, new_status: isActive}, function (data) {
            if (!data.success) {
                alert('Error al actualizar el estado del dispositivo. Inténtalo de nuevo.');
                updateDeviceList();
            }
            $('.device-toggle').prop('disabled', false);
            isUpdating = false;  // Indica que la solicitud POST se ha completado
        }).fail(function () {
            alert('Error al enviar la solicitud de actualización. Inténtalo de nuevo.');
            updateDeviceList();
            $('.device-toggle').prop('disabled', false);
            isUpdating = false;  // Indica que la solicitud POST se ha completado
        });
    }

    $(document).on('change', '.device-toggle', function () {
        var deviceId = $(this).data('device-id');
        var isActive = $(this).is(':checked');
        $(this).prop('disabled', true);
        sendUpdateRequest(deviceId, isActive);
    });

    setInterval(function () {
        $.get("/get_updated_devices", function (data) {
            var deviceList = $("#device-list");
            deviceList.children().each(function () {
                var deviceId = $(this).find('.device-toggle').data('device-id');
                var device = data.devices_db.find(d => d.id === deviceId);
                if (device) {
                    var isActive = $(this).find('.device-toggle').is(':checked');
                    if (isActive !== device.status[0].value) {
                        $(this).find('.device-toggle').prop('checked', device.status[0].value);
                        sendUpdateRequest(device.id, device.status[0].value);
                    }
                }
            });
        });
    }, 4000);  // Actualiza la lista de dispositivos cada 5 segundos

    updateDeviceList();  // Actualiza la lista de dispositivos al cargar la página
});