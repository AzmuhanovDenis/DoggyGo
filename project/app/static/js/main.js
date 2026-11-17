document.addEventListener('DOMContentLoaded', () => {
    const burgerBtn = document.querySelector('.burger-btn');
    const mainNav = document.querySelector('.main-nav');

    if (burgerBtn && mainNav) {
        burgerBtn.addEventListener('click', () => {
            const isExpanded = burgerBtn.getAttribute('aria-expanded') === 'true';
            burgerBtn.setAttribute('aria-expanded', String(!isExpanded));
            mainNav.classList.toggle('is-open');
        });
    }
});
