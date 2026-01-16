function getCookieValue(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

document.addEventListener('DOMContentLoaded', () => {
    const btns = document.querySelectorAll('.mark-read-btn');

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            const notifId = btn.dataset.id;
            const url = btn.dataset.url;
            const card = document.getElementById(`notif-${notifId}`);
            const workflow = document.getElementById(`workflow-${notifId}`);

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookieValue('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    btn.remove();
                    if (workflow) {
                        workflow.style.transition = "all 0.5s ease";
                        workflow.style.height = "0";
                        workflow.style.opacity = "0";
                        workflow.style.margin = "0";
                        workflow.style.padding = "0";
                        setTimeout(() => workflow.remove(), 500);
                    }
                    if (card) {
                        card.classList.remove('new-notification-anim', 'bg-white');
                        card.classList.add('bg-light', 'opacity-75');
                    }
                }
            });
        });
    });
});
