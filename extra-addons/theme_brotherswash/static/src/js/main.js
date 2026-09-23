/** @odoo-module **/

function bwdInit() {
    // Loader
    var loader = document.getElementById('bwdLoader');
    if (loader) {
        window.addEventListener('load', function () {
            setTimeout(function () { loader.classList.add('bwd-loader--done'); }, 800);
        });
    }

    // Mobile nav toggle
    var toggle = document.querySelector('.bwd-nav-toggle');
    var mobileNav = document.getElementById('bwdMobileNav');
    if (toggle && mobileNav) {
        toggle.addEventListener('click', function () {
            toggle.classList.toggle('active');
            mobileNav.classList.toggle('bwd-mobile-nav--open');
        });
    }
    function closeNav() {
        if (toggle) toggle.classList.remove('active');
        if (mobileNav) mobileNav.classList.remove('bwd-mobile-nav--open');
    }
    document.querySelectorAll('.bwd-mobile-nav__link').forEach(function (a) {
        a.addEventListener('click', closeNav);
    });

    // Header scroll effect
    var header = document.getElementById('bwdHeader');
    if (header) {
        window.addEventListener('scroll', function () {
            header.classList.toggle('bwd-header--scrolled', window.scrollY > 50);
        });
    }

    // Smooth scroll for anchor links (handles both #bwd-xxx and /#bwd-xxx)
    document.querySelectorAll('a[href*="#bwd"]').forEach(function (a) {
        a.addEventListener('click', function (e) {
            var href = a.getAttribute('href');
            var hash = href.indexOf('#') !== -1 ? href.substring(href.indexOf('#')) : null;
            if (hash) {
                var target = document.querySelector(hash);
                if (target) {
                    e.preventDefault();
                    closeNav();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // Reviews infinite scroll
    (function () {
        var rows = document.querySelectorAll('.bwd-reviews__row');
        rows.forEach(function (row, i) {
            var cards = row.querySelectorAll('.bwd-review-card');
            var halfCount = cards.length / 2;
            var setWidth = 0;
            for (var c = 0; c < halfCount; c++) {
                setWidth += cards[c].offsetWidth + parseFloat(getComputedStyle(cards[c]).marginRight);
            }
            var speed = 0.5;
            var direction = i === 0 ? -1 : 1;
            var pos = direction === 1 ? -setWidth : 0;
            var paused = false;
            row.addEventListener('mouseenter', function () { paused = true; });
            row.addEventListener('mouseleave', function () { paused = false; });
            function tick() {
                if (!paused) {
                    pos += speed * direction;
                    if (direction === -1 && pos <= -setWidth) pos += setWidth;
                    if (direction === 1 && pos >= 0) pos -= setWidth;
                }
                row.style.transform = 'translateX(' + pos + 'px)';
                requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
        });
    })();

    // Scroll reveal (IntersectionObserver)
    window.bwdRevealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('bwd-reveal--visible');
            }
        });
    }, { threshold: 0.1 });
    document.querySelectorAll('.bwd-reveal').forEach(function (el) {
        window.bwdRevealObserver.observe(el);
    });
}

/** Observe new .bwd-reveal elements inside a container (called by widgets after render). */
window.bwdObserveReveals = function (container) {
    if (!window.bwdRevealObserver) return;
    (container || document).querySelectorAll('.bwd-reveal:not(.bwd-reveal--visible)').forEach(function (el) {
        window.bwdRevealObserver.observe(el);
    });
};

// Run when DOM is ready - handle both cases
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bwdInit);
} else {
    bwdInit();
}
