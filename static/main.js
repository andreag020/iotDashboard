$(document).ready(function () {
    var isUpdating = false;

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

    function updateChart(deviceData) {
        var ctx = document.getElementById('usageChart').getContext('2d');

        // Verificar si usageChart está definido y es una instancia de Chart antes de destruirlo
        if (window.usageChart instanceof Chart) {
            window.usageChart.destroy();
        }

        var datasets = deviceData.map(function (device, index) {
            return {
                label: device.name,
                data: device.data,
                borderColor: index % 2 === 0 ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)',
                fill: false
            };
        });

        // Crear un nuevo gráfico y almacenarlo en la variable usageChart
        window.usageChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: deviceData[0].labels,  // Asume que todos los dispositivos tienen las mismas etiquetas
                datasets: datasets
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function getDeviceDataAndUpdateChart() {
        $.get("/get_device_data", function (data) {
            // Formatear los datos de los dispositivos
            var deviceData = data.device_data.map(function (device) {
                return {
                    ...device,
                    data: Array.isArray(device.status) ? device.status.map(status => status.code === 'active_time' ? Number(status.value) : 0) : []  // Si device.status no es un array, usa un array vacío
                };
            });

            // Añadir registros de depuración
            console.log("Datos de dispositivos obtenidos:", deviceData);

            if (deviceData.length > 0 && deviceData[0].labels && deviceData[0].labels.length > 0) {
                updateChart(deviceData);
            } else {
                console.error("No se encontraron datos de dispositivos o las etiquetas están vacías");
            }
        }).fail(function () {
            alert('Error al obtener los datos de los dispositivos. Inténtalo de nuevo más tarde.');
        });
    }

    function updateActiveTimeChart(activeTimeData) {
        var ctx = document.getElementById('activeTimeChart').getContext('2d');

        if (window.activeTimeChart instanceof Chart) {
            window.activeTimeChart.destroy();
        }

        window.activeTimeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: activeTimeData.labels,  // Usamos las etiquetas horarias
                datasets: [{
                    label: 'Active Time by Hour',
                    data: activeTimeData.data,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                var hour = tooltipItem.label.split(':')[0];  // Obtener la hora
                                var device_names = activeTimeData.device_names[hour];
                                return `${tooltipItem.dataset.label}: ${tooltipItem.raw} hours (${device_names})`;
                            }
                        }
                    }
                }
            }
        });
    }

    function getActiveTimeDataAndUpdateChart() {
        $.get("/get_active_time_by_hour", function (data) {
            console.log("Datos de tiempo activo obtenidos:", data);
            if (data.labels.length > 0) {
                updateActiveTimeChart(data);
            } else {
                console.error("No se encontraron datos de tiempo activo o las etiquetas están vacías");
            }
        }).fail(function () {
            alert('Error al obtener los datos de tiempo activo. Inténtalo de nuevo más tarde.');
        });
    }

    $(document).on('change', '.device-toggle', function () {
        var deviceId = $(this).data('device-id');
        var isActive = $(this).is(':checked');
        $(this).prop('disabled', true); // Deshabilita el interruptor
        sendUpdateRequest(deviceId, isActive);
    });

    setInterval(function () {
        getDeviceDataAndUpdateChart();
        updateDeviceList();
        getActiveTimeDataAndUpdateChart();
    }, 5000);

    updateDeviceList(); // Actualiza la lista de dispositivos al cargar la página
    getActiveTimeDataAndUpdateChart(); // Obtiene y grafica el tiempo activo al cargar la página
});