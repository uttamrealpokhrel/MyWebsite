
function scrollToSection() {
    const about = document.getElementById("about");
    if (about) {
        about.scrollIntoView({ behavior: "smooth" });
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    // Optionally, persist theme
    if (document.body.classList.contains('dark-theme')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
}

// On load, set theme from storage
window.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-theme');
    }
});
// theme.js contains only client-side helpers (no server code)