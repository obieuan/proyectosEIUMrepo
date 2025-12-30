// Reveal animations on scroll
(() => {
    const revealItems = document.querySelectorAll(".reveal");
    if (!revealItems.length) return;

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    obs.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12 }
    );

    revealItems.forEach((item) => observer.observe(item));
})();

// Filter form auto-submit
(() => {
    const filterForm = document.querySelector(".filters");
    if (!filterForm) return;

    const textInput = filterForm.querySelector("input[name='texto']");
    let textTimer = null;

    if (textInput) {
        textInput.addEventListener("input", () => {
            if (textTimer) clearTimeout(textTimer);
            textTimer = setTimeout(() => filterForm.submit(), 600);
        });
    }

    filterForm.addEventListener("change", (event) => {
        if (event.target === textInput) return;
        filterForm.submit();
    });
})();

// Featured carousel with infinite loop
document.addEventListener("DOMContentLoaded", () => {
    const carousel = document.getElementById("featured-carousel");
    if (!carousel) return;

    const prevBtn = document.querySelector(".carousel-prev");
    const nextBtn = document.querySelector(".carousel-next");
    if (!prevBtn || !nextBtn) return;

    // LIMPIAR nodos de texto vacíos/invisibles del carousel
    carousel.childNodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
            node.remove();
        }
    });

    const originalCards = Array.from(carousel.querySelectorAll(".project-card"));
    const totalOriginal = originalCards.length;
    
    if (totalOriginal === 0) return;

    // Si hay muy pocas cards, no hacer loop infinito
    if (totalOriginal <= 2) {
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
    }

    // Número de clones a cada lado
    const cloneCount = Math.min(totalOriginal, 4);

    // Función para crear un clon limpio
    const createClone = (card) => {
        const clone = card.cloneNode(true);
        clone.classList.add('carousel-clone');
        clone.classList.remove('reveal'); // Quitar clase reveal para evitar conflictos
        clone.classList.add('is-visible'); // Asegurar que sea visible
        return clone;
    };

    // Clonar las últimas N al principio (insertar siempre al inicio)
    for (let i = cloneCount - 1; i >= 0; i--) {
        const clone = createClone(originalCards[totalOriginal - 1 - i]);
        carousel.insertBefore(clone, carousel.firstChild);
    }
    
    // Clonar las primeras N al final
    for (let i = 0; i < cloneCount; i++) {
        const clone = createClone(originalCards[i]);
        carousel.appendChild(clone);
    }

    // Calcular el ancho de una card + gap usando getBoundingClientRect para precisión
    const getCardWidth = () => {
        const cards = carousel.querySelectorAll(".project-card");
        if (cards.length < 2) return 300;
        // Calcular distancia entre el inicio de dos cards consecutivas
        const rect1 = cards[0].getBoundingClientRect();
        const rect2 = cards[1].getBoundingClientRect();
        return rect2.left - rect1.left;
    };

    // Posición inicial: después de los clones del inicio
    const setInitialPosition = () => {
        const cardWidth = getCardWidth();
        carousel.style.scrollBehavior = 'auto';
        carousel.scrollLeft = cardWidth * cloneCount;
        carousel.style.scrollBehavior = 'smooth';
    };

    // Esperar a que todo se renderice completamente
    requestAnimationFrame(() => {
        requestAnimationFrame(setInitialPosition);
    });

    // Variables de control
    let isAnimating = false;
    let scrollEndTimer = null;

    // Función para hacer scroll de una card
    const scrollByOne = (direction) => {
        if (isAnimating) return;
        isAnimating = true;
        
        const cardWidth = getCardWidth();
        carousel.scrollBy({
            left: direction === 'next' ? cardWidth : -cardWidth,
            behavior: 'smooth'
        });
        
        // Liberar después de la animación
        setTimeout(() => {
            isAnimating = false;
        }, 400);
    };

    // Verificar y ajustar posición para loop infinito
    const checkAndLoop = () => {
        const cardWidth = getCardWidth();
        const currentScroll = carousel.scrollLeft;
        
        // Rango válido de los originales
        const startOfOriginals = cardWidth * cloneCount;
        const endOfOriginals = cardWidth * (cloneCount + totalOriginal - 1);

        // Tolerancia para detectar que salimos del rango
        const tolerance = cardWidth * 0.3;

        if (currentScroll < startOfOriginals - tolerance) {
            // Estamos en los clones del inicio, saltar al final de los originales
            carousel.style.scrollBehavior = 'auto';
            carousel.scrollLeft = currentScroll + (cardWidth * totalOriginal);
            requestAnimationFrame(() => {
                carousel.style.scrollBehavior = 'smooth';
            });
        } else if (currentScroll > endOfOriginals + tolerance) {
            // Estamos en los clones del final, saltar al inicio de los originales
            carousel.style.scrollBehavior = 'auto';
            carousel.scrollLeft = currentScroll - (cardWidth * totalOriginal);
            requestAnimationFrame(() => {
                carousel.style.scrollBehavior = 'smooth';
            });
        }
    };

    // Manejar el evento scroll con debounce
    carousel.addEventListener('scroll', () => {
        if (scrollEndTimer) clearTimeout(scrollEndTimer);
        scrollEndTimer = setTimeout(checkAndLoop, 100);
    });

    // Event listeners para botones
    nextBtn.addEventListener('click', () => scrollByOne('next'));
    prevBtn.addEventListener('click', () => scrollByOne('prev'));

    // Recalcular en resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(setInitialPosition, 250);
    });
});