/**
 * schedule_management.js - Schedule management functionality for routes
 * This script handles assigning and removing schedules from routes
 */

(function () {
  "use strict";

  let currentRouteForSchedules = null;

  /**
   * Initialize schedule management functionality
   */
  function init() {
    const manageScheduleBtns = document.querySelectorAll('.manage-schedules-btn');
    manageScheduleBtns.forEach(btn => {
      btn.addEventListener('click', handleManageSchedulesClick);
    });
    
    // Setup add schedule buttons
    setupAddScheduleButtons();
  }
  
  /**
   * Setup event listeners for add schedule buttons
   */
  function setupAddScheduleButtons() {
    const addScheduleBtns = document.querySelectorAll('.add-schedule-btn');
    addScheduleBtns.forEach(btn => {
      btn.addEventListener('click', handleAddSingleSchedule);
    });
  }
  
  /**
   * Handle click on manage schedules button
   */
  function handleManageSchedulesClick(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const routeSlug = button.dataset.routeSlug;
    const routeName = button.dataset.routeName;
    
    currentRouteForSchedules = {
      slug: routeSlug,
      name: routeName
    };
    
    // Update modal title
    document.getElementById('manage-schedule-route-name').textContent = routeName;
    
    // Load schedules for this route
    loadRouteSchedules(routeSlug);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('manageSchedulesModal'));
    modal.show();
  }
  
  /**
   * Load schedules for a route
   */
  function loadRouteSchedules(routeSlug) {
    showLoading(true);
    
    fetch(`${MANAGE_SCHEDULES_API_URL}?route_slug=${routeSlug}`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': CSRF_TOKEN
      }
    })
      .then(response => response.json())
      .then(data => {
        showLoading(false);
        
        if (data.success) {
          displayCurrentSchedules(data.route_schedules);
        } else {
          showNotification(data.message, 'danger');
        }
      })
      .catch(error => {
        showLoading(false);
        showNotification('An error occurred while loading schedules.', 'danger');
        console.error('Load schedules error:', error);
      });
  }
  
  /**
   * Display current schedules for the route
   */
  function displayCurrentSchedules(schedules) {
    const container = document.getElementById('current-schedules-list');
    
    if (!schedules || schedules.length === 0) {
      container.innerHTML = '<p class="text-muted mb-0"><i class="fa-solid fa-info-circle me-1"></i>No schedules assigned yet</p>';
      updateAllSchedulesButtons(schedules);
      return;
    }
    
    container.innerHTML = schedules.map(schedule => `
      <div class="d-flex justify-content-between align-items-center mb-2">
        <span>
          <i class="fa-solid fa-clock me-2"></i>${schedule.name} 
          (${formatTime(schedule.start_time)} - ${formatTime(schedule.end_time)})
        </span>
        <button class="btn btn-sm btn-outline-danger remove-schedule-btn" 
                data-schedule-slug="${schedule.slug}"
                title="Remove this schedule">
          <i class="fa-solid fa-times"></i>
        </button>
      </div>
    `).join('');
    
    // Add event listeners to remove buttons
    container.querySelectorAll('.remove-schedule-btn').forEach(btn => {
      btn.addEventListener('click', handleRemoveSchedule);
    });
    
    // Update the add buttons in the all schedules list
    updateAllSchedulesButtons(schedules);
  }
  
  /**
   * Update add/remove buttons in all schedules list based on current schedules
   */
  function updateAllSchedulesButtons(currentSchedules) {
    const currentSlugs = currentSchedules ? currentSchedules.map(s => s.slug) : [];
    const allScheduleItems = document.querySelectorAll('#all-schedules-list .schedule-item');
    
    allScheduleItems.forEach(item => {
      const scheduleSlug = item.dataset.scheduleSlug;
      const button = item.querySelector('button');
      
      if (!button) return;
      
      if (currentSlugs.includes(scheduleSlug)) {
        // Schedule is already added, show as disabled
        button.className = 'btn btn-sm btn-outline-secondary';
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-check me-1"></i>Added';
        button.title = 'Schedule already added';
        // Remove old event listeners
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
      } else {
        // Schedule is not added, show add button
        button.className = 'btn btn-sm btn-success add-schedule-btn';
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-plus me-1"></i>Add';
        button.title = 'Add this schedule to route';
        // Clone button to remove old event listeners
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
        // Add new event listener
        newButton.addEventListener('click', handleAddSingleSchedule);
      }
    });
  }
  
  /**
   * Format time string (HH:MM:SS to h:mm AM/PM)
   */
  function formatTime(timeStr) {
    const [hours, minutes] = timeStr.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
  }
  
  /**
   * Handle adding a single schedule
   */
  function handleAddSingleSchedule(e) {
    e.preventDefault();
    
    if (!currentRouteForSchedules) return;
    
    const button = e.currentTarget;
    const scheduleSlug = button.dataset.scheduleSlug;
    
    showLoading(true);
    
    fetch(MANAGE_SCHEDULES_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify({
        route_slug: currentRouteForSchedules.slug,
        schedule_slugs: [scheduleSlug]
      })
    })
      .then(response => response.json())
      .then(data => {
        showLoading(false);
        
        if (data.success) {
          showNotification(data.message, 'success');
          displayCurrentSchedules(data.schedules);
          updateRouteSchedulesInUI(data.route.slug, data.schedules);
        } else {
          showNotification(data.message, 'danger');
        }
      })
      .catch(error => {
        showLoading(false);
        showNotification('An error occurred while adding schedule.', 'danger');
        console.error('Add schedule error:', error);
      });
  }
  
  /**
   * Handle removing a schedule
   */
  function handleRemoveSchedule(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const scheduleSlug = button.dataset.scheduleSlug;
    
    if (!currentRouteForSchedules) return;
    
    showLoading(true);
    
    fetch(MANAGE_SCHEDULES_API_URL, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify({
        route_slug: currentRouteForSchedules.slug,
        schedule_slugs: [scheduleSlug]
      })
    })
      .then(response => response.json())
      .then(data => {
        showLoading(false);
        
        if (data.success) {
          showNotification(data.message, 'success');
          // Update current schedules display and buttons
          displayCurrentSchedules(data.schedules);
          updateRouteSchedulesInUI(data.route.slug, data.schedules);
        } else {
          showNotification(data.message, 'danger');
        }
      })
      .catch(error => {
        showLoading(false);
        showNotification('An error occurred while removing schedule.', 'danger');
        console.error('Remove schedule error:', error);
      });
  }
  
  /**
   * Update route schedules display in the UI
   */
  function updateRouteSchedulesInUI(routeSlug, schedules) {
    const routeCard = document.querySelector(`.route-card[data-route-slug="${routeSlug}"]`);
    if (!routeCard) return;
    
    let schedulesContainer = routeCard.querySelector('.route-schedules');
    
    if (schedules.length === 0) {
      // Remove schedules container if no schedules
      if (schedulesContainer) {
        schedulesContainer.remove();
      }
      return;
    }
    
    // Create schedules container if it doesn't exist
    if (!schedulesContainer) {
      schedulesContainer = document.createElement('div');
      schedulesContainer.className = 'route-schedules mt-2';
      schedulesContainer.dataset.routeSlug = routeSlug;
      routeCard.querySelector('.route-header').appendChild(schedulesContainer);
    }
    
    // Update schedules display
    schedulesContainer.innerHTML = `
      <small class="text-muted d-block mb-1">
        <i class="fa-solid fa-clock me-1"></i>Active Schedules:
      </small>
      <div class="schedules-list">
        ${schedules.map(schedule => `
          <span class="badge bg-info me-1 mb-1">
            ${schedule.name} (${formatTime(schedule.start_time)} - ${formatTime(schedule.end_time)})
          </span>
        `).join('')}
      </div>
    `;
  }
  
  // Helper functions (use from stop_transfer.js)
  function showLoading(show) {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.display = show ? "flex" : "none";
    }
  }
  
  function showNotification(message, type = "info") {
    const notification = document.getElementById("transfer-notification");
    const messageElement = document.getElementById("notification-message");

    if (notification && messageElement) {
      notification.className = "alert alert-dismissible fade show";
      notification.classList.add(`alert-${type}`);
      messageElement.textContent = message;
      notification.style.display = "block";

      if (type !== "danger") {
        setTimeout(() => {
          const bsAlert = new bootstrap.Alert(notification);
          bsAlert.close();
        }, 5000);
      }
    }
  }
  
  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
