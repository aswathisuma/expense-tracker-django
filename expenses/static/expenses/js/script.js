// Small UI helpers. The app works fully without JavaScript; this only adds convenience.
document.addEventListener('DOMContentLoaded', function () {
    // Mobile navigation toggle
    var navToggle = document.querySelector('[data-nav-toggle]');
    var navLinks = document.getElementById('main-nav');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            var isOpen = navLinks.classList.toggle('open');
            navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }

    // Close buttons on flash messages
    document.querySelectorAll('[data-dismiss-alert]').forEach(function (button) {
        button.addEventListener('click', function () {
            button.closest('.alert').remove();
        });
    });

    // Success messages fade away after a few seconds
    document.querySelectorAll('.alert-success').forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            setTimeout(function () { alert.remove(); }, 300);
        }, 4000);
    });

    // Apply category / month filters as soon as a new option is chosen
    document.querySelectorAll('[data-auto-submit]').forEach(function (select) {
        select.addEventListener('change', function () {
            select.form.submit();
        });
    });
});
