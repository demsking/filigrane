// --------------------------------------------------------------------------
// Filigrane Landing Page Interactive Logic
// --------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // 1. Theme Toggle Logic
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;

    // Check saved theme or system preference
    const savedTheme = localStorage.getItem('filigrane-theme');
    if (savedTheme) {
        htmlEl.setAttribute('data-theme', savedTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        htmlEl.setAttribute('data-theme', 'light');
    }

    const setThemeButtonState = () => {
        if (!themeToggleBtn) return;
        const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
        themeToggleBtn.setAttribute('aria-pressed', String(currentTheme === 'light'));
    };
    setThemeButtonState();

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('filigrane-theme', newTheme);
            setThemeButtonState();
        });
    }

    // 1b. Mobile Navigation Toggle
    const navToggleBtn = document.getElementById('nav-toggle');
    const headerContainer = document.getElementById('header-container');
    const mainNav = document.getElementById('main-nav');

    const closeNav = () => {
        if (!headerContainer || !navToggleBtn) return;
        headerContainer.classList.remove('nav-open');
        navToggleBtn.setAttribute('aria-expanded', 'false');
    };

    if (navToggleBtn && headerContainer) {
        navToggleBtn.addEventListener('click', () => {
            const isOpen = headerContainer.classList.toggle('nav-open');
            navToggleBtn.setAttribute('aria-expanded', String(isOpen));
        });

        // Close the menu after a nav link is chosen
        mainNav?.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', closeNav);
        });

        // Close on Escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') closeNav();
        });

        // Close when clicking outside the menu
        document.addEventListener('click', (event) => {
            const clickedInsideNav = headerContainer.contains(event.target);
            if (!clickedInsideNav) closeNav();
        });

        // Reset state if the viewport grows back to desktop size
        window.addEventListener('resize', () => {
            if (window.innerWidth > 640) closeNav();
        });
    }

    // 2. Copy Command Box Interactivity (works for every .btn-copy on the page)
    document.querySelectorAll('.btn-copy').forEach((btn) => {
        const cmdBox = btn.closest('.cmd-box');
        const cmdTextEl = cmdBox?.querySelector('.cmd-text');
        if (!cmdTextEl) return;

        const originalLabel = btn.querySelector('.copy-label')?.textContent ?? null;
        const originalAriaLabel = btn.getAttribute('aria-label');

        btn.addEventListener('click', async () => {
            const textToCopy = cmdTextEl.textContent.trim();
            try {
                await navigator.clipboard.writeText(textToCopy);

                // Show copied state
                btn.classList.add('copied');
                const labelSpan = btn.querySelector('.copy-label');
                if (labelSpan) labelSpan.textContent = 'Copied!';
                btn.setAttribute('aria-label', 'Copied to clipboard');

                setTimeout(() => {
                    btn.classList.remove('copied');
                    if (labelSpan && originalLabel) labelSpan.textContent = originalLabel;
                    if (originalAriaLabel) btn.setAttribute('aria-label', originalAriaLabel);
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }
        });
    });
});
