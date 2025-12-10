document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const closeSidebar = document.getElementById('close-sidebar');
  const btnExperience = document.getElementById('btn-experience');
  const experienceModal = new bootstrap.Modal(document.getElementById('experienceModal'));
  const reserveModalEl = document.getElementById('reserveModal');
  const reserveModal = new bootstrap.Modal(reserveModalEl);
  const reserveForm = document.getElementById('reserveForm');
  const reserveAlert = document.getElementById('reserve-alert');
  const notLogged = document.getElementById('not-logged');

  // Tu usuario actual desde el template
  const currentUserEmail = "{{ current_user_email }}";

  // Sidebar open/close
  hamburger?.addEventListener('click', () => {
    sidebar.classList.add('open');
    hamburger.style.display = 'none'; // ocultar botón al abrir
  });

  closeSidebar?.addEventListener('click', () => {
    sidebar.classList.remove('open');
    hamburger.style.display = 'block'; // mostrar botón al cerrar
  });

  // Experiencia
  btnExperience?.addEventListener('click', () => experienceModal.show());
  document.getElementById('btn-experiencia-inline')?.addEventListener('click', () => experienceModal.show());

  // FullCalendar init
  const calendarEl = document.getElementById('calendar');
  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    selectable: true,
    height: 'auto',
    headerToolbar: {
      left: 'title',
      center: '',
      right: 'prev,next today'
    },
    eventDisplay: 'block',
    events: '/events',
    select: function(info) {
      const sd = info.startStr.substring(0,10);
      let edDate = new Date(info.end);
      edDate.setDate(edDate.getDate()-1);
      const ed = edDate.toISOString().substring(0,10);

      document.getElementById('start_date').value = sd;
      document.getElementById('end_date').value = ed;
      document.getElementById('start_time').value = '09:00';
      document.getElementById('end_time').value = '12:00';

      fetch('/profile').then(r => {
        if (r.status === 200) {
          notLogged.classList.add('d-none');
        } else {
          notLogged.classList.remove('d-none');
        }
      });

      reserveAlert.innerHTML = '';
      reserveModal.show();
    },
    eventClick: function(info) {
    const props = info.event.extendedProps;
    let message = `Reservado.\nUsuario: ${props.user_email || 'anónimo'}\nTel: ${props.phone || 'No disponible'}`;
    
    // Solo si es tu reserva, permitir eliminar
    if (props.is_current_user) {
        if (confirm(message + "\n\n¿Deseas cancelar esta reserva?")) {
            fetch(`/cancel/${info.event.id}`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                if (data.ok) info.event.remove();  // elimina del calendario
            })
            .catch(err => alert('Error al cancelar.'));
        }
    } else {
        alert(message);
    }
}




  });

  calendar.render();

  // Formulario de reserva
  reserveForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    reserveAlert.innerHTML = '';
    const form = new FormData(reserveForm);
    const payload = {
      start_date: form.get('start_date'),
      start_time: form.get('start_time'),
      end_date: form.get('end_date'),
      end_time: form.get('end_time'),
      neuro: form.get('neuro')
    };

    try {
      const res = await fetch('/book', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        reserveAlert.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
        calendar.refetchEvents();
        setTimeout(()=> reserveModal.hide(), 1100);
      } else {
        reserveAlert.innerHTML = `<div class="alert alert-danger">${data.message || 'Error'}</div>`;
      }
    } catch (err) {
      reserveAlert.innerHTML = `<div class="alert alert-danger">Error de red.</div>`;
    }
  });
});
