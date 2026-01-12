document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPass').value;
            const errorP = document.getElementById('loginError');
            errorP.innerText = '';

            try {
                const res = await fetch('/api/v1/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();

                if (res.ok) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    window.location.href = '/dashboard';
                } else {
                    errorP.innerText = data.message;
                }
            } catch (err) {
                errorP.innerText = "Connection error";
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('regName').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPass').value;
            const phone = document.getElementById('regPhone').value;
            const gender = document.getElementById('regGender').value;
            const errorP = document.getElementById('regError');
            errorP.innerText = '';

            try {
                const res = await fetch('/api/v1/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password, phone, gender })
                });
                const data = await res.json();

                if (res.ok) {
                    alert('Registration successful! Please login.');
                    window.location.reload();
                } else {
                    errorP.innerText = data.message;
                }
            } catch (err) {
                errorP.innerText = "Connection error";
            }
        });
    }
});
