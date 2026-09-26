/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

function bwInitConfigurator() {
    var form = document.getElementById('bwBookingForm');
    if (!form) return;

    var priceMap = window.bwPriceMap || {};
    var totalEl = document.getElementById('bwTotalPrice');
    var vehicleRadios = form.querySelectorAll('input[name="vehicle_type_id"]');
    var serviceChecks = form.querySelectorAll('input[type="checkbox"][name^="service_"]');

    var currencySuffix = form.dataset.currencySuffix || ',- Kč';
    var msgSelectVehicle = _t("Please select your vehicle type.");
    var msgSelectService = _t("Please select at least one service.");
    var msgSending = _t("Sending...");

    function getSelectedVehicle() {
        var checked = form.querySelector('input[name="vehicle_type_id"]:checked');
        return checked ? parseInt(checked.value, 10) : null;
    }

    function updatePrices() {
        var vtId = getSelectedVehicle();
        var total = 0;

        serviceChecks.forEach(function (cb) {
            var svcId = cb.name.replace('service_', '');
            var priceEl = form.querySelector('.bw-service-price[data-service-id="' + svcId + '"]');
            if (!priceEl) return;

            var valueEl = priceEl.querySelector('.bw-price-value');
            var data = priceMap[svcId] && priceMap[svcId][vtId];

            if (vtId && data) {
                var prefix = data.prefix ? data.prefix + ' ' : '';
                valueEl.textContent = prefix + formatPrice(data.price);
                priceEl.classList.remove('bw-price-na');
            } else if (vtId) {
                var anyPrice = priceMap[svcId];
                var firstKey = anyPrice ? Object.keys(anyPrice)[0] : null;
                if (firstKey) {
                    var fallback = anyPrice[firstKey];
                    var prefix = fallback.prefix ? fallback.prefix + ' ' : '';
                    valueEl.textContent = prefix + formatPrice(fallback.price);
                    priceEl.classList.remove('bw-price-na');
                } else {
                    valueEl.textContent = '--';
                    priceEl.classList.add('bw-price-na');
                }
            } else {
                valueEl.textContent = '--';
            }

            if (cb.checked && vtId) {
                var priceVal = 0;
                if (data) {
                    priceVal = data.price;
                } else {
                    var any = priceMap[svcId];
                    var fk = any ? Object.keys(any)[0] : null;
                    if (fk) priceVal = any[fk].price;
                }
                total += priceVal;
            }
        });

        totalEl.textContent = formatPrice(total) + currencySuffix;

        var totalBar = document.getElementById('bwTotalBar');
        if (totalBar) {
            totalBar.classList.toggle('bw-total-visible', total > 0);
        }
    }

    function formatPrice(num) {
        return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }

    // Vehicle type selection
    vehicleRadios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            form.querySelectorAll('.bw-vehicle-card').forEach(function (card) {
                card.classList.remove('bw-vehicle-card--active');
            });
            this.closest('.bw-vehicle-card').classList.add('bw-vehicle-card--active');
            updatePrices();
        });
    });

    // Service checkbox changes
    serviceChecks.forEach(function (cb) {
        cb.addEventListener('change', function () {
            this.closest('.bw-service-item').classList.toggle('bw-service-item--selected', this.checked);
            updatePrices();
        });
    });

    // Form validation
    form.addEventListener('submit', function (e) {
        if (!getSelectedVehicle()) {
            e.preventDefault();
            alert(msgSelectVehicle);
            document.getElementById('bwStep1').scrollIntoView({behavior: 'smooth'});
            return;
        }

        var anyChecked = false;
        serviceChecks.forEach(function (cb) {
            if (cb.checked) anyChecked = true;
        });
        if (!anyChecked) {
            e.preventDefault();
            alert(msgSelectService);
            document.getElementById('bwStep2').scrollIntoView({behavior: 'smooth'});
            return;
        }

        // Ad attribution (gclid / fbclid / utm) for the booking and CRM lead
        var trackingInput = document.getElementById('bwTrackingInput');
        if (trackingInput && window.bwTracking) {
            trackingInput.value = JSON.stringify(window.bwTracking.getAttribution());
        }

        var btn = document.getElementById('bwSubmitBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + msgSending;
        }
    });

    updatePrices();
}

// The frontend bundle is loaded lazily, DOMContentLoaded may be long gone
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bwInitConfigurator);
} else {
    bwInitConfigurator();
}
