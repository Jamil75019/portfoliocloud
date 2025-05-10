document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.progress-bar').forEach(bar => {
        const width = bar.getAttribute('data-width');
        setTimeout(() => {
            bar.style.width = width + '%';
        }, 300);
    });

    const header = document.querySelector('header');
    const cloud = document.createElement('div');
    cloud.classList.add('cloud-animation');
    header.appendChild(cloud);
});
