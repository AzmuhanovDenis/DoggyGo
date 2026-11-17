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

    const filterForm = document.getElementById('catalog-filters-form');
    const resultsContainer = document.getElementById('sitters-results-container');
    const resultsCounter = document.getElementById('results-counter');
    const loader = document.getElementById('catalog-loader');
    const sortSelect = document.getElementById('sort-select');
    const hiddenSortInput = document.getElementById('hidden-sort-input');

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderSitterCard(sitter) {
        const avatarHtml = sitter.photo_url
            ? `<img src="${escapeHtml(sitter.photo_url)}" alt="${escapeHtml(sitter.name)}" width="64" height="64" loading="lazy">`
            : `<span>${escapeHtml(sitter.initials)}</span>`;

        const verifiedBadge = sitter.is_approved
            ? '<span class="badge badge-success">&#10003; Проверен куратором</span>'
            : '';

        let tagsHtml = '';
        if (sitter.weight_incompatible) {
            tagsHtml = `<span class="badge badge-danger">Ограничение: собаки до ${sitter.max_weight} кг</span>`;
        } else {
            if (sitter.accepts_large_dogs) {
                tagsHtml += '<span class="badge badge-success">Крупные породы</span>';
            }
            sitter.behaviors.forEach((behavior) => {
                tagsHtml += `<span class="badge badge-success">${escapeHtml(behavior)}</span>`;
            });
        }

        const actionButton = sitter.weight_incompatible
            ? '<button type="button" class="btn btn-disabled" disabled>Не подходит по весу</button>'
            : `<a href="${escapeHtml(sitter.detail_url)}" class="btn btn-primary">Выбрать слот</a>`;

        return `
            <article class="card-box sitter-card">
                <div class="sitter-avatar" aria-hidden="true">${avatarHtml}</div>
                <div class="sitter-info">
                    <div class="sitter-header-row">
                        <h2 class="sitter-name">${escapeHtml(sitter.name)}</h2>
                        ${verifiedBadge}
                    </div>
                    <p class="sitter-meta">
                        Районы: ${escapeHtml(sitter.areas)} &bull; До ${sitter.max_weight} кг &bull; Рейтинг ${escapeHtml(sitter.rating)} (${sitter.reviews_count} отзывов)
                    </p>
                    <div class="tags-row">${tagsHtml}</div>
                </div>
                <div class="sitter-action">
                    <div class="sitter-price">${sitter.rate} &#8381; / час</div>
                    ${actionButton}
                </div>
            </article>
        `;
    }
        async function fetchFilteredSitters() {
        if (!filterForm || !resultsContainer) return;

        const apiUrl = filterForm.dataset.apiUrl;
        if (!apiUrl) return;

        const formData = new FormData(filterForm);
        const params = new URLSearchParams(formData);

        if (loader) loader.hidden = false;

        try {
            const response = await fetch(`${apiUrl}?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) throw new Error('Ошибка загрузки каталога');

            const data = await response.json();

            if (resultsCounter) {
                resultsCounter.textContent = `Найдено ${data.total_count} специалиста`;
            }

            if (data.results && data.results.length > 0) {
                const cardsHtml = data.results.map(renderSitterCard).join('');
                resultsContainer.innerHTML = `<div class="sitters-list">${cardsHtml}</div>`;
            } else {
                resultsContainer.innerHTML = `
                    <div class="card-box empty-state">
                        <h2>Подходящих специалистов не найдено</h2>
                        <p>Попробуйте изменить параметры поиска или сбросить фильтры.</p>
                    </div>
                `;
            }
        } catch (err) {
            console.error(err);
        } finally {
            if (loader) loader.hidden = true;
        }
    }

    if (filterForm && resultsContainer) {
        let searchTimer = null;
        const nameInput = document.getElementById('filter-q');
        const areaSelect = document.getElementById('filter-area');
        const weightInput = document.getElementById('filter-weight');
        const behaviorCheckboxes = filterForm.querySelectorAll('input[name="behaviors"]');

        if (nameInput) {
            nameInput.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(fetchFilteredSitters, 300);
            });
        }

        if (weightInput) {
            weightInput.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(fetchFilteredSitters, 300);
            });
        }

        if (areaSelect) {
            areaSelect.addEventListener('change', fetchFilteredSitters);
        }

        behaviorCheckboxes.forEach((checkbox) => {
            checkbox.addEventListener('change', fetchFilteredSitters);
        });

        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                if (hiddenSortInput) hiddenSortInput.value = sortSelect.value;
                fetchFilteredSitters();
            });
        }
    }

    const formsToValidate = document.querySelectorAll('form[method="post"]');

    function setFieldError(input, message) {
        input.classList.add('is-invalid');
        let errorEl = input.parentElement.querySelector('.js-field-error');
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'js-field-error';
            input.parentElement.appendChild(errorEl);
        }
        errorEl.textContent = message;
    }

    function clearFieldError(input) {
        input.classList.remove('is-invalid');
        const errorEl = input.parentElement.querySelector('.js-field-error');
        if (errorEl) errorEl.remove();
    }

    formsToValidate.forEach((form) => {
        form.addEventListener('submit', (event) => {
            let hasErrors = false;
            const inputs = form.querySelectorAll('input, select, textarea');

            inputs.forEach((input) => {
                if (input.type === 'hidden' || input.type === 'checkbox' || input.type === 'file') return;

                clearFieldError(input);
                const val = input.value.trim();

                if (input.hasAttribute('required') && !val) {
                    setFieldError(input, 'Пожалуйста, заполните это обязательное поле.');
                    hasErrors = true;
                    return;
                }

                if (input.type === 'email' && val) {
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailRegex.test(val)) {
                        setFieldError(input, 'Введите корректный адрес электронной почты (например, name@example.ru).');
                        hasErrors = true;
                        return;
                    }
                }

                if (input.name === 'phone' && val) {
                    const phoneRegex = /^\+?[0-9]{10,15}$/;
                    if (!phoneRegex.test(val)) {
                        setFieldError(input, 'Телефон должен содержать 10–15 цифр (возможен + в начале).');
                        hasErrors = true;
                        return;
                    }
                }

                const minLen = input.getAttribute('minlength');
                if (minLen && val.length > 0 && val.length < Number(minLen)) {
                    setFieldError(input, `Минимальная длина поля — ${minLen} символов.`);
                    hasErrors = true;
                    return;
                }

                if (input.name === 'weight_kg' && val) {
                    const weightNum = Number(val);
                    if (Number.isNaN(weightNum) || weightNum < 0.1 || weightNum > 150) {
                        setFieldError(input, 'Укажите вес собаки от 0.1 до 150 кг.');
                        hasErrors = true;
                    }
                }
            });

            const bookingSlotInput = form.querySelector('#id_slot_id');
            if (bookingSlotInput && !bookingSlotInput.value) {
                hasErrors = true;
                alert('Пожалуйста, выберите свободный временной слот расписания выше.');
            }

            if (hasErrors) {
                event.preventDefault();
            }
        });
    });
});
