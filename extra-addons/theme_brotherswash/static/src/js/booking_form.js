/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.BwdBookingForm = publicWidget.Widget.extend({
    selector: '#bwdBookingForm',

    start() {
        this._super(...arguments);
        this.priceMap = {};
        this.vehicleTypes = [];
        this.categories = [];
        this.selectedVehicle = null;
        this.selectedServices = new Set();
        this.currentStep = 1;
        this._loadData();
    },

    _loadData() {
        var self = this;
        this.el.innerHTML = '<p style="text-align:center;padding:2rem;opacity:.6">' + _t("Loading services…") + '</p>';
        rpc('/bw/api/services', {}).then(function (data) {
            self.vehicleTypes = data.vehicle_types || [];
            self.categories = data.categories || [];
            self.priceMap = {};
            var services = data.services || [];
            var pm = data.price_map || {};
            services.forEach(function (svc) {
                self.priceMap[String(svc.id)] = {};
                var svcPrices = pm[svc.id] || pm[String(svc.id)] || {};
                Object.keys(svcPrices).forEach(function (vtId) {
                    self.priceMap[String(svc.id)][String(vtId)] = svcPrices[vtId];
                });
            });
            self.categories.forEach(function (cat) {
                cat.services = services.filter(function (s) {
                    return s.category_id === cat.id;
                });
            });
            self._render();
        }).catch(function () {
            self.el.innerHTML = '<p style="text-align:center;padding:2rem;color:#c00">' + _t("Failed to load services. Try refreshing the page.") + '</p>';
        });
    },

    _render() {
        var self = this;
        this.el.innerHTML = '';

        // Step indicator
        var indicator = document.createElement('div');
        indicator.className = 'bwd-wizard-indicator';
        indicator.id = 'bwdWizardIndicator';
        for (var i = 1; i <= 3; i++) {
            var dot = document.createElement('div');
            dot.className = 'bwd-wizard-dot' + (i === 1 ? ' bwd-wizard-dot--active' : '');
            dot.dataset.step = i;
            var labels = [_t("Vehicle type"), _t("Services"), _t("Contact")];
            dot.innerHTML = '<span class="bwd-wizard-dot__num">' + i + '</span><span class="bwd-wizard-dot__label">' + labels[i - 1] + '</span>';
            if (i < 3) {
                var line = document.createElement('div');
                line.className = 'bwd-wizard-line';
                indicator.appendChild(dot);
                indicator.appendChild(line);
            } else {
                indicator.appendChild(dot);
            }
        }
        this.el.appendChild(indicator);

        // Step 1: Vehicle type
        var step1 = this._renderVehicleStep();
        step1.id = 'bwdStep1';
        this.el.appendChild(step1);

        // Step 2: Services (hidden)
        var step2 = this._renderServicesStep();
        step2.id = 'bwdStep2';
        step2.style.display = 'none';
        this.el.appendChild(step2);

        // Step 3: Contact (hidden)
        var step3 = this._renderContactStep();
        step3.id = 'bwdStep3';
        step3.style.display = 'none';
        this.el.appendChild(step3);

        // Success message (hidden)
        var success = document.createElement('div');
        success.className = 'bwd-booking-success';
        success.id = 'bwdBookingSuccess';
        success.style.display = 'none';
        success.innerHTML = '<div class="bwd-booking-success__icon">&#10003;</div>' +
            '<h3>' + _t("Thank you for your reservation!") + '</h3>' +
            '<p>' + _t("We have sent a confirmation to your email. We will contact you to confirm the appointment.") + '</p>';
        this.el.appendChild(success);
    },

    _goToStep(step) {
        this.currentStep = step;
        // Hide all steps
        for (var i = 1; i <= 3; i++) {
            var el = this.el.querySelector('#bwdStep' + i);
            if (el) el.style.display = i === step ? 'block' : 'none';
        }
        // Update indicator
        var dots = this.el.querySelectorAll('.bwd-wizard-dot');
        var lines = this.el.querySelectorAll('.bwd-wizard-line');
        dots.forEach(function (d) {
            var s = parseInt(d.dataset.step);
            d.classList.toggle('bwd-wizard-dot--active', s === step);
            d.classList.toggle('bwd-wizard-dot--done', s < step);
        });
        lines.forEach(function (l, idx) {
            l.classList.toggle('bwd-wizard-line--done', idx < step - 1);
        });
        // Update summary when entering step 3
        if (step === 3) this._updateSummary();
        // Scroll to form
        this.el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    _renderVehicleStep() {
        var self = this;
        var step = document.createElement('div');
        step.className = 'bwd-booking-step';
        step.innerHTML = '<h3 class="bwd-booking-step__title"><span class="bwd-booking-step__num">1</span> ' + _t("Vehicle type") + '</h3>' +
            '<p class="bwd-booking-step__desc">' + _t("Select your vehicle type for correct price calculation.") + '</p>';

        var vehicles = document.createElement('div');
        vehicles.className = 'bwd-booking-vehicles';
        this.vehicleTypes.forEach(function (vt) {
            var label = document.createElement('label');
            label.className = 'bwd-booking-vehicle';
            var input = document.createElement('input');
            input.type = 'radio';
            input.name = 'bwd_vehicle_type';
            input.value = vt.id;
            input.addEventListener('change', function () {
                self.selectedVehicle = vt.id;
                self._updatePrices();
                // Enable next button
                var btn = self.el.querySelector('#bwdNextStep1');
                if (btn) {
                    btn.disabled = false;
                    btn.classList.add('bwd-btn--active');
                }
            });
            var span = document.createElement('span');
            span.className = 'bwd-booking-vehicle__inner';
            span.textContent = vt.name;
            label.appendChild(input);
            label.appendChild(span);
            vehicles.appendChild(label);
        });
        step.appendChild(vehicles);

        // Next button
        var nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'bwd-btn bwd-btn--filled bwd-booking-next';
        nextBtn.id = 'bwdNextStep1';
        nextBtn.disabled = true;
        nextBtn.textContent = _t("Continue to service selection");
        nextBtn.addEventListener('click', function () {
            if (!self.selectedVehicle) return;
            self._goToStep(2);
        });
        step.appendChild(nextBtn);

        return step;
    },

    _renderServicesStep() {
        var self = this;
        var step = document.createElement('div');
        step.className = 'bwd-booking-step';
        step.innerHTML = '<h3 class="bwd-booking-step__title"><span class="bwd-booking-step__num">2</span> ' + _t("Services") + '</h3>' +
            '<p class="bwd-booking-step__desc">' + _t("Select the services you want to order.") + '</p>';

        this.categories.forEach(function (cat) {
            var group = document.createElement('div');
            group.className = 'bwd-booking-group';
            group.innerHTML = '<h4 class="bwd-booking-group__title">' + self._esc(cat.name) + '</h4>';

            var list = document.createElement('div');
            list.className = 'bwd-booking-services';

            cat.services.forEach(function (svc) {
                var label = document.createElement('label');
                label.className = 'bwd-booking-svc' + (svc.is_highlighted ? ' bwd-booking-svc--hl' : '');
                label.dataset.svcId = svc.id;

                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = svc.id;
                cb.addEventListener('change', function () {
                    if (this.checked) {
                        self.selectedServices.add(svc.id);
                    } else {
                        self.selectedServices.delete(svc.id);
                    }
                    label.classList.toggle('bwd-booking-svc--selected', this.checked);
                    self._updateTotal();
                    // Enable/disable next button
                    var btn = self.el.querySelector('#bwdNextStep2');
                    if (btn) {
                        btn.disabled = self.selectedServices.size === 0;
                        btn.classList.toggle('bwd-btn--active', self.selectedServices.size > 0);
                    }
                });

                var info = document.createElement('div');
                info.className = 'bwd-booking-svc__info';
                info.innerHTML = '<strong>' + self._esc(svc.name) + '</strong>' +
                    (svc.short_description ? '<small>' + self._esc(svc.short_description) + '</small>' : '');

                var price = document.createElement('span');
                price.className = 'bwd-booking-svc__price';
                price.dataset.svcId = svc.id;
                price.textContent = '--';

                label.appendChild(cb);
                label.appendChild(info);
                label.appendChild(price);
                list.appendChild(label);
            });

            group.appendChild(list);
            step.appendChild(group);
        });

        // Total display
        var totalRow = document.createElement('div');
        totalRow.className = 'bwd-booking-total';
        totalRow.id = 'bwdTotal';
        totalRow.innerHTML = _t("Total:") + ' <strong id="bwdTotalPrice">0,- Kč</strong>';
        step.appendChild(totalRow);

        // Navigation buttons
        var nav = document.createElement('div');
        nav.className = 'bwd-booking-nav';

        var backBtn = document.createElement('button');
        backBtn.type = 'button';
        backBtn.className = 'bwd-btn bwd-booking-back';
        backBtn.textContent = '← ' + _t("Back");
        backBtn.addEventListener('click', function () { self._goToStep(1); });

        var nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'bwd-btn bwd-btn--filled bwd-booking-next';
        nextBtn.id = 'bwdNextStep2';
        nextBtn.disabled = true;
        nextBtn.textContent = _t("Continue to contact");
        nextBtn.addEventListener('click', function () {
            if (!self.selectedServices.size) return;
            self._goToStep(3);
        });

        nav.appendChild(backBtn);
        nav.appendChild(nextBtn);
        step.appendChild(nav);

        return step;
    },

    _renderContactStep() {
        var self = this;
        var step = document.createElement('div');
        step.className = 'bwd-booking-step';

        step.innerHTML =
            '<h3 class="bwd-booking-step__title"><span class="bwd-booking-step__num">3</span> ' + _t("Contact details") + '</h3>' +
            '<p class="bwd-booking-step__desc">' + _t("Fill in your details to complete the reservation.") + '</p>' +
            '<div class="bwd-booking-summary" id="bwdSummary"></div>' +
            '<div class="bwd-booking-fields">' +
                '<input type="text" id="bwdName" class="bwd-booking-input" placeholder="' + _t("Full name") + ' *" required/>' +
                '<input type="email" id="bwdEmail" class="bwd-booking-input" placeholder="' + _t("Email") + ' *" required/>' +
                '<input type="tel" id="bwdPhone" class="bwd-booking-input" placeholder="' + _t("Phone") + ' *" required/>' +
                '<input type="text" id="bwdVehicleInfo" class="bwd-booking-input" placeholder="' + _t("Car make / model") + '"/>' +
                '<input type="datetime-local" id="bwdDate" class="bwd-booking-input"/>' +
                '<textarea id="bwdNote" class="bwd-booking-input" rows="2" placeholder="' + _t("Note") + '"></textarea>' +
            '</div>' +
            '<div class="bwd-booking-total">' + _t("Total:") + ' <strong id="bwdTotalPriceFinal">0,- Kč</strong></div>';

        // Navigation buttons
        var nav = document.createElement('div');
        nav.className = 'bwd-booking-nav';

        var backBtn = document.createElement('button');
        backBtn.type = 'button';
        backBtn.className = 'bwd-btn bwd-booking-back';
        backBtn.textContent = '← ' + _t("Back");
        backBtn.addEventListener('click', function () { self._goToStep(2); });

        var submitBtn = document.createElement('button');
        submitBtn.type = 'button';
        submitBtn.className = 'bwd-btn bwd-btn--filled bwd-btn--active bwd-booking-submit';
        submitBtn.id = 'bwdSubmitBooking';
        submitBtn.textContent = _t("Submit reservation");
        submitBtn.addEventListener('click', function () { self._submitBooking(this); });

        nav.appendChild(backBtn);
        nav.appendChild(submitBtn);
        step.appendChild(nav);

        return step;
    },

    _updateSummary() {
        var self = this;
        var el = this.el.querySelector('#bwdSummary');
        if (!el) return;

        var vtName = '';
        this.vehicleTypes.forEach(function (vt) {
            if (vt.id === self.selectedVehicle) vtName = vt.name;
        });

        var svcs = [];
        var total = 0;
        var hasPrefix = false;
        this.selectedServices.forEach(function (svcId) {
            var data = self._getPrice(svcId);
            var svcName = '';
            self.categories.forEach(function (cat) {
                cat.services.forEach(function (s) {
                    if (s.id === svcId) svcName = s.name;
                });
            });
            var priceStr = data ? (data.prefix ? data.prefix + ' ' : '') + self._fmtPrice(data.price) + ',-' : '--';
            if (data) {
                total += data.price;
                if (data.prefix) hasPrefix = true;
            }
            svcs.push('<div class="bwd-booking-summary__item"><span>' + self._esc(svcName) + '</span><span>' + priceStr + '</span></div>');
        });

        el.innerHTML =
            '<div class="bwd-booking-summary__vehicle">' + self._esc(vtName) + '</div>' +
            svcs.join('');

        var totalEl = this.el.querySelector('#bwdTotalPriceFinal');
        if (totalEl) totalEl.textContent = (hasPrefix ? _t("from") + ' ' : '') + this._fmtPrice(total) + ',- Kč';
    },

    _getPrice(svcId) {
        var map = this.priceMap[String(svcId)];
        if (!map) return null;
        var vtId = String(this.selectedVehicle);
        if (map[vtId]) return map[vtId];
        // Fallback: flat-rate service with single price entry
        var keys = Object.keys(map);
        return keys.length === 1 ? map[keys[0]] : null;
    },

    _updatePrices() {
        var self = this;
        this.el.querySelectorAll('.bwd-booking-svc__price').forEach(function (el) {
            var svcId = el.dataset.svcId;
            var data = self._getPrice(svcId);
            if (self.selectedVehicle && data) {
                el.textContent = (data.prefix ? data.prefix + ' ' : '') + self._fmtPrice(data.price) + ',-';
            } else {
                el.textContent = '--';
            }
        });
        this._updateTotal();
    },

    _updateTotal() {
        var self = this;
        var total = 0;
        var hasPrefix = false;
        this.selectedServices.forEach(function (svcId) {
            var data = self._getPrice(svcId);
            if (data) {
                total += data.price;
                if (data.prefix) hasPrefix = true;
            }
        });
        var el = this.el.querySelector('#bwdTotalPrice');
        if (el) el.textContent = (hasPrefix ? _t("from") + ' ' : '') + this._fmtPrice(total) + ',- Kč';
    },

    _fmtPrice(n) {
        return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    },

    _esc(str) {
        var d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    },

    _submitBooking(btn) {
        var self = this;
        var name = document.getElementById('bwdName').value.trim();
        var email = document.getElementById('bwdEmail').value.trim();
        var phone = document.getElementById('bwdPhone').value.trim();
        if (!name || !email || !phone) { alert(_t("Please fill in name, email and phone.")); return; }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { alert(_t("Please enter a valid email address.")); return; }

        btn.disabled = true;
        btn.textContent = _t("Submitting...");

        // Build service list with prices from frontend
        var serviceData = [];
        this.selectedServices.forEach(function (svcId) {
            var data = self._getPrice(svcId);
            serviceData.push({
                id: svcId,
                price: data ? data.price : 0,
            });
        });

        rpc('/bw/api/booking/submit', {
            customer_name: name,
            customer_email: email,
            customer_phone: phone,
            vehicle_type_id: this.selectedVehicle,
            vehicle_info: document.getElementById('bwdVehicleInfo').value,
            preferred_date: document.getElementById('bwdDate').value,
            customer_note: document.getElementById('bwdNote').value,
            service_ids: Array.from(this.selectedServices),
            service_data: serviceData,
            tracking: window.bwTracking ? window.bwTracking.getAttribution() : {},
        }).then(function (result) {
            if (result && result.success) {
                // Conversion for Meta Pixel / GA4 / Google Ads / GTM (bw_booking tracking.js)
                if (window.bwTracking) {
                    try {
                        window.bwTracking.bookingSubmitted(result.tracking);
                    } catch (e) {
                        console.warn(e);
                    }
                }
                self.el.querySelector('#bwdStep3').style.display = 'none';
                self.el.querySelector('#bwdWizardIndicator').style.display = 'none';
                document.getElementById('bwdBookingSuccess').style.display = 'block';
            } else if (result && result.error === 'invalid_email') {
                alert(_t("Please enter a valid email address."));
                btn.disabled = false;
                btn.textContent = _t("Submit reservation");
            } else {
                alert(_t("Error submitting. Please try again."));
                btn.disabled = false;
                btn.textContent = _t("Submit reservation");
            }
        }).catch(function () {
            alert(_t("Network error. Please try again."));
            btn.disabled = false;
            btn.textContent = _t("Submit reservation");
        });
    },
});
