/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

// ─── Shared cache so multiple widgets don't duplicate requests ───
var _companyCache = null;
var _companyPromise = null;
function getCompanyInfo() {
    if (_companyCache) return Promise.resolve(_companyCache);
    if (!_companyPromise) {
        _companyPromise = rpc('/bw/api/company-info', {}).then(function (data) {
            _companyCache = data;
            return data;
        });
    }
    return _companyPromise;
}

var _servicesCache = null;
var _servicesPromise = null;
function getServices() {
    if (_servicesCache) return Promise.resolve(_servicesCache);
    if (!_servicesPromise) {
        _servicesPromise = rpc('/bw/api/services', {}).then(function (data) {
            _servicesCache = data;
            return data;
        });
    }
    return _servicesPromise;
}

function formatPrice(price) {
    return Math.round(price).toLocaleString('cs-CZ').replace(/\u00a0/g, ' ') + ',-';
}

function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ─── Hero: phone link + social icons ───
publicWidget.registry.BwdHeroCompany = publicWidget.Widget.extend({
    selector: '[data-snippet="s_bwd_hero"]',

    start() {
        this._super(...arguments);
        var self = this;
        getCompanyInfo().then(function (co) { self._render(co); });
    },

    _render(co) {
        // Phone
        var phoneEl = this.el.querySelector('[data-bwd-company="phone"]');
        if (phoneEl) {
            if (co.phone) {
                phoneEl.innerHTML = '<a href="tel:' + escapeHtml(co.phone_clean) + '" class="bwd-hero__phone">' + escapeHtml(co.phone) + '</a>';
            } else {
                phoneEl.style.display = 'none';
            }
        }

        // Address
        var addrEl = this.el.querySelector('[data-bwd-company="address"]');
        if (addrEl) {
            if (co.street || co.city) {
                var parts = [];
                if (co.street) parts.push(escapeHtml(co.street));
                if (co.city) parts.push((co.zip ? escapeHtml(co.zip) + ' ' : '') + escapeHtml(co.city));
                var query = encodeURIComponent((co.street || '') + ', ' + (co.zip || '') + ' ' + (co.city || ''));
                var pinSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg> ';
                addrEl.innerHTML = '<a href="https://maps.google.com/?q=' + query + '" target="_blank" rel="noopener" class="bwd-hero__address-link">' + pinSvg + parts.join(', ') + '</a>';
            } else {
                addrEl.style.display = 'none';
            }
        }

        // Socials
        var socialsEl = this.el.querySelector('[data-bwd-company="socials"]');
        if (socialsEl) {
            var html = '';
            if (co.social_instagram) {
                html += '<a href="' + escapeHtml(co.social_instagram) + '" target="_blank" rel="noopener" class="bwd-hero__social" aria-label="Instagram">'
                    + '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="5"/><circle cx="17.5" cy="6.5" r="1.5"/></svg></a>';
            }
            if (co.social_facebook) {
                html += '<a href="' + escapeHtml(co.social_facebook) + '" target="_blank" rel="noopener" class="bwd-hero__social" aria-label="Facebook">'
                    + '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z"/></svg></a>';
            }
            if (co.email) {
                html += '<a href="mailto:' + escapeHtml(co.email) + '" class="bwd-hero__social" aria-label="Email">'
                    + '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg></a>';
            }
            socialsEl.innerHTML = html;
        }
        window.bwdObserveReveals && window.bwdObserveReveals(this.el);
    },
});

// ─── Contact: company info block ───
publicWidget.registry.BwdContactCompany = publicWidget.Widget.extend({
    selector: '[data-snippet="s_bwd_contact"]',

    start() {
        this._super(...arguments);
        var self = this;
        getCompanyInfo().then(function (co) { self._render(co); });
    },

    _render(co) {
        var el = this.el.querySelector('[data-bwd-company="contact-info"]');
        if (!el) return;

        var html = '';
        if (co.street || co.city) {
            var query = encodeURIComponent((co.street || '') + ', ' + (co.zip || '') + ' ' + (co.city || ''));
            html += '<div class="bwd-contact__item"><div><strong>' + _t("Address") + '</strong><br/>'
                + '<a href="https://maps.google.com/?q=' + query + '" target="_blank" rel="noopener">';
            if (co.street) html += escapeHtml(co.street) + '<br/>';
            if (co.zip) html += escapeHtml(co.zip) + ' ';
            if (co.city) html += escapeHtml(co.city);
            html += '</a></div></div>';
        }
        if (co.phone) {
            html += '<div class="bwd-contact__item"><div><strong>' + _t("Phone") + '</strong><br/>'
                + '<a href="tel:' + escapeHtml(co.phone_clean) + '">' + escapeHtml(co.phone) + '</a></div></div>';
        }
        if (co.email) {
            html += '<div class="bwd-contact__item"><div><strong>' + _t("Email") + '</strong><br/>'
                + '<a href="mailto:' + escapeHtml(co.email) + '">' + escapeHtml(co.email) + '</a></div></div>';
        }
        if (co.social_instagram) {
            html += '<div class="bwd-contact__item"><div><strong>' + _t("Instagram") + '</strong><br/>'
                + '<a href="' + escapeHtml(co.social_instagram) + '" target="_blank" rel="noopener">@brotherswashdetailing</a></div></div>';
        }
        if (co.social_facebook) {
            html += '<div class="bwd-contact__item"><div><strong>' + _t("Facebook") + '</strong><br/>'
                + '<a href="' + escapeHtml(co.social_facebook) + '" target="_blank" rel="noopener">Brothers Wash Detailing</a></div></div>';
        }
        el.innerHTML = html;
        window.bwdObserveReveals && window.bwdObserveReveals(this.el);
    },
});

// ─── Footer: copyright line ───
publicWidget.registry.BwdFooterCompany = publicWidget.Widget.extend({
    selector: '[data-snippet="s_bwd_footer"]',

    start() {
        this._super(...arguments);
        var self = this;
        getCompanyInfo().then(function (co) { self._render(co); });
    },

    _render(co) {
        var el = this.el.querySelector('[data-bwd-company="copyright"]');
        if (el) {
            el.textContent = '\u00A9 ' + co.year + ' ' + (co.name || 'Brothers Wash Detailing');
        }
    },
});

// ─── Service catalog widgets (premium, programs, extras) ───
publicWidget.registry.BwdServiceCatalog = publicWidget.Widget.extend({
    selector: '[data-bwd-services]',

    start() {
        this._super(...arguments);
        this.categoryType = this.el.dataset.bwdServices;
        var self = this;
        getServices().then(function (data) { self._render(data); });
    },

    _render(data) {
        var type = this.categoryType;
        var categories = (data.categories || []).filter(function (c) { return c.category_type === type; });
        var services = data.services || [];
        var priceMap = data.price_map || {};

        if (!categories.length) return;

        var html = '';
        categories.forEach(function (cat) {
            var catServices = services.filter(function (s) { return s.category_id === cat.id; });
            if (!catServices.length) return;

            html += '<h2 class="bwd-section-title bwd-reveal">' + escapeHtml(cat.name) + '</h2>';
            html += '<div class="bwd-section-line"></div>';
            if (cat.description) {
                html += '<p class="bwd-section-subtitle bwd-reveal">' + escapeHtml(cat.description) + '</p>';
            }

            if (type === 'extra') {
                html += this._renderExtras(catServices, priceMap);
            } else if (type === 'premium') {
                html += this._renderPremium(catServices, priceMap);
            } else {
                html += this._renderPrograms(catServices, priceMap);
            }
        }.bind(this));

        if (type === 'extra') {
            html += '<div class="bwd-surcharge bwd-reveal">' + _t("Dirt surcharge \u2013 from 25%") + '</div>';
        }

        this.el.innerHTML = html;
        window.bwdObserveReveals && window.bwdObserveReveals(this.el);
    },

    _renderPrograms(services, priceMap) {
        var html = '<div class="row g-3">';
        services.forEach(function (svc) {
            var cls = 'bwd-card bwd-reveal' + (svc.is_highlighted ? ' bwd-card--featured' : '');
            html += '<div class="col-12 col-md-6 col-lg-3"><div class="' + cls + '">';
            if (svc.is_highlighted) {
                html += '<div class="bwd-card__badge">' + _t("Most popular") + '</div>';
            }
            html += '<div class="bwd-card__header">';
            html += '<span class="bwd-card__icon"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/></svg></span>';
            html += '<h3>' + escapeHtml(svc.name) + '</h3>';
            if (svc.duration_info) {
                html += '<span class="bwd-card__duration">' + escapeHtml(svc.duration_info) + '</span>';
            }
            html += '</div>';
            if (svc.short_description) {
                html += '<div class="bwd-card__subtitle">' + escapeHtml(svc.short_description) + '</div>';
            }
            if (svc.description) {
                html += svc.description;
            }
            html += this._renderPrices(svc, priceMap);
            html += '</div></div>';
        }.bind(this));
        html += '</div>';
        return html;
    },

    _renderPremium(services, priceMap) {
        var html = '<div class="row g-3">';
        services.forEach(function (svc) {
            var cls = 'bwd-card bwd-card--premium bwd-reveal' + (svc.is_highlighted ? ' bwd-card--highlight' : '');
            html += '<div class="col-12 col-md-4"><div class="' + cls + '">';
            html += '<div class="bwd-card__icon-block"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></div>';
            html += '<h3>' + escapeHtml(svc.name) + '</h3>';
            if (svc.short_description) {
                html += '<div class="bwd-card__subtitle">' + escapeHtml(svc.short_description) + '</div>';
            }
            if (svc.description) {
                html += svc.description;
            }
            html += this._renderPrices(svc, priceMap);
            html += '</div></div>';
        }.bind(this));
        html += '</div>';
        return html;
    },

    _renderExtras(services, priceMap) {
        var half = Math.ceil(services.length / 2);
        var col1 = services.slice(0, half);
        var col2 = services.slice(half);

        var html = '<div class="row g-0">';
        html += '<div class="col-12 col-md-6">' + this._renderExtraCol(col1, priceMap) + '</div>';
        html += '<div class="col-12 col-md-6">' + this._renderExtraCol(col2, priceMap) + '</div>';
        html += '</div>';
        return html;
    },

    _renderExtraCol(services, priceMap) {
        var html = '';
        services.forEach(function (svc) {
            html += '<div class="bwd-extra"><span>' + escapeHtml(svc.name) + '</span>';
            var prices = priceMap[svc.id] || {};
            var firstKey = Object.keys(prices)[0];
            if (firstKey) {
                var p = prices[firstKey];
                html += '<span class="bwd-extra__price">';
                if (p.prefix) html += escapeHtml(p.prefix) + ' ';
                html += formatPrice(p.price);
                html += '</span>';
            }
            html += '</div>';
        });
        return html;
    },

    _renderPrices(svc, priceMap) {
        var prices = priceMap[svc.id] || {};
        var keys = Object.keys(prices);
        if (!keys.length) return '';

        var html = '<div class="bwd-card__prices">';
        // We need vehicle type names — they're in the data
        var vehicleTypes = (_servicesCache && _servicesCache.vehicle_types) || [];
        var vtMap = {};
        vehicleTypes.forEach(function (vt) { vtMap[vt.id] = vt.name; });

        keys.forEach(function (vtId) {
            var p = prices[vtId];
            html += '<div class="bwd-card__price-row">';
            html += '<span>' + escapeHtml(vtMap[vtId] || '');
            if (p.prefix) html += ' ' + escapeHtml(p.prefix);
            html += '</span>';
            html += '<span class="bwd-price">' + formatPrice(p.price) + '</span>';
            html += '</div>';
        });
        html += '</div>';
        return html;
    },
});
