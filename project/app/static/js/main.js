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

    const slotButtons = document.querySelectorAll('.slot-btn[data-slot-id]');
    const slotInput = document.getElementById('id_slot_id');
    const priceDisplay = document.getElementById('booking-price');

    if (slotButtons.length > 0 && slotInput) {
        slotButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
                slotButtons.forEach((item) => item.classList.remove('is-selected'));
                btn.classList.add('is-selected');
                slotInput.value = btn.dataset.slotId;

                if (priceDisplay && btn.dataset.slotPrice) {
                    priceDisplay.textContent = btn.dataset.slotPrice;
                }
            });
        });
    }
});
