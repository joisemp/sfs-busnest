/**
 * stop_transfer.js - Drag and Drop functionality for transferring stops between routes
 *
 * This script handles the HTML5 drag-and-drop interface for moving stops from one route to another.
 * It communicates with the backend API to perform the actual transfer and updates the UI accordingly.
 * Also includes inline editing functionality for stop names.
 */

(function () {
  "use strict";

  // State management
  let draggedElement = null;
  let draggedStopData = null;
  let editingElement = null;
  let pendingTransfer = null; // Store pending transfer data for modal confirmation
  let pendingAddStop = null; // Store route data for adding new stop
  let pendingDeleteStop = null; // Store stop data for deletion confirmation
  let pendingDeleteRoute = null; // Store route data for deletion confirmation

  /**
   * Initialize drag-and-drop and inline editing functionality
   */
  function init() {
    const stopItems = document.querySelectorAll(".stop-item");
    const dropZones = document.querySelectorAll(".drop-zone");
    const addStopButtons = document.querySelectorAll(".add-stop-btn");
    const deleteStopButtons = document.querySelectorAll(".delete-stop-btn");
    const deleteRouteButtons = document.querySelectorAll(".delete-route-btn");
    const createRouteBtn = document.getElementById("createRouteBtn");

    // Setup drag events for all stops
    stopItems.forEach((stop) => {
      stop.addEventListener("dragstart", handleDragStart);
      stop.addEventListener("dragend", handleDragEnd);

      // Setup inline editing on stop names
      const stopNameElement = stop.querySelector(".stop-name");
      if (stopNameElement) {
        stopNameElement.addEventListener("dblclick", handleStopNameEdit);
      }
    });

    // Setup drop zones
    dropZones.forEach((zone) => {
      zone.addEventListener("dragover", handleDragOver);
      zone.addEventListener("dragenter", handleDragEnter);
      zone.addEventListener("dragleave", handleDragLeave);
      zone.addEventListener("drop", handleDrop);
    });

    // Setup modal confirm button
    const confirmBtn = document.getElementById("confirmTransferBtn");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", handleModalConfirm);
    }

    // Setup add stop buttons
    addStopButtons.forEach((btn) => {
      btn.addEventListener("click", handleAddStopClick);
    });

    // Setup add stop modal confirm button
    const confirmAddStopBtn = document.getElementById("confirmAddStopBtn");
    if (confirmAddStopBtn) {
      confirmAddStopBtn.addEventListener("click", handleAddStopConfirm);
    }
    
    // Setup delete stop buttons
    deleteStopButtons.forEach((btn) => {
      btn.addEventListener("click", handleDeleteStopClick);
    });
    
    // Setup delete stop modal confirm button
    const confirmDeleteStopBtn = document.getElementById("confirmDeleteStopBtn");
    if (confirmDeleteStopBtn) {
      confirmDeleteStopBtn.addEventListener("click", handleDeleteStopConfirm);
    }

    // Setup Enter key for stop name input
    const stopNameInput = document.getElementById("stopNameInput");
    if (stopNameInput) {
      stopNameInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          handleAddStopConfirm();
        }
      });

      // Clear validation on input
      stopNameInput.addEventListener("input", function () {
        this.classList.remove("is-invalid");
      });
    }

    // Clear input when modal is hidden
    const addStopModal = document.getElementById("addStopModal");
    if (addStopModal) {
      addStopModal.addEventListener("hidden.bs.modal", function () {
        document.getElementById("stopNameInput").value = "";
        document.getElementById("stopNameInput").classList.remove("is-invalid");
      });
    }
    
    // Setup create route button
    if (createRouteBtn) {
      createRouteBtn.addEventListener("click", handleCreateRouteClick);
    }
    
    // Setup create route modal confirm button
    const confirmCreateRouteBtn = document.getElementById("confirmCreateRouteBtn");
    if (confirmCreateRouteBtn) {
      confirmCreateRouteBtn.addEventListener("click", handleCreateRouteConfirm);
    }
    
    // Setup route name input Enter key
    const routeNameInput = document.getElementById("routeNameInput");
    if (routeNameInput) {
      routeNameInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          handleCreateRouteConfirm();
        }
      });
      
      // Clear validation on input
      routeNameInput.addEventListener("input", function () {
        this.classList.remove("is-invalid");
      });
    }
    
    // Clear route name input when modal is hidden
    const createRouteModal = document.getElementById("createRouteModal");
    if (createRouteModal) {
      createRouteModal.addEventListener("hidden.bs.modal", function () {
        document.getElementById("routeNameInput").value = "";
        document.getElementById("routeNameInput").classList.remove("is-invalid");
      });
    }
    
    // Setup delete route buttons
    deleteRouteButtons.forEach((btn) => {
      btn.addEventListener("click", handleDeleteRouteClick);
    });
    
    // Setup delete route modal confirm button
    const confirmDeleteRouteBtn = document.getElementById("confirmDeleteRouteBtn");
    if (confirmDeleteRouteBtn) {
      confirmDeleteRouteBtn.addEventListener("click", handleDeleteRouteConfirm);
    }
  }

  /**
   * Handle double-click on stop name to enable inline editing
   */
  function handleStopNameEdit(e) {
    e.stopPropagation();

    // Prevent editing if already editing another stop
    if (editingElement) {
      return;
    }

    const stopNameElement = this;
    const stopItem = stopNameElement.closest(".stop-item");
    const currentName = stopNameElement.textContent.trim();
    const stopSlug = stopItem.dataset.stopSlug;

    // Create input field
    const input = document.createElement("input");
    input.type = "text";
    input.className = "stop-name-input";
    input.value = currentName;
    input.maxLength = 200;

    // Store reference
    editingElement = stopNameElement;

    // Replace text with input
    stopNameElement.style.display = "none";
    stopNameElement.parentNode.insertBefore(input, stopNameElement);

    // Focus and select text
    input.focus();
    input.select();

    // Handle save on Enter key
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        saveStopName(stopSlug, input.value.trim(), stopNameElement, input);
      } else if (e.key === "Escape") {
        cancelEdit(stopNameElement, input);
      }
    });

    // Handle save on blur (clicking outside)
    input.addEventListener("blur", function () {
      // Small delay to allow other click events to process
      setTimeout(() => {
        if (input.value.trim() !== currentName) {
          saveStopName(stopSlug, input.value.trim(), stopNameElement, input);
        } else {
          cancelEdit(stopNameElement, input);
        }
      }, 200);
    });
  }

  /**
   * Save the updated stop name via API
   */
  function saveStopName(stopSlug, newName, stopNameElement, inputElement) {
    if (!newName || newName.length < 2) {
      showNotification("Stop name must be at least 2 characters", "warning");
      inputElement.focus();
      return;
    }

    // Show loading state
    showLoading(true);

    fetch(UPDATE_STOP_NAME_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        stop_slug: stopSlug,
        new_name: newName,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);

        if (data.success) {
          // Update the stop name in the DOM
          stopNameElement.textContent = data.stop.name;
          stopNameElement.style.display = "";
          inputElement.remove();
          editingElement = null;

          showNotification(data.message, "success");
        } else {
          showNotification(data.message, "danger");
          inputElement.focus();
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while updating the stop name. Please try again.",
          "danger"
        );
        console.error("Update stop name error:", error);
        inputElement.focus();
      });
  }

  /**
   * Cancel editing and restore original state
   */
  function cancelEdit(stopNameElement, inputElement) {
    stopNameElement.style.display = "";
    inputElement.remove();
    editingElement = null;
  }

  /**
   * Handle drag start event
   */
  function handleDragStart(e) {
    // Don't allow dragging while editing
    if (editingElement) {
      e.preventDefault();
      return;
    }
    
    // Don't allow dragging when clicking on buttons
    if (e.target.closest('.delete-stop-btn') || e.target.closest('button')) {
      e.preventDefault();
      return;
    }

    draggedElement = this;

    // Store stop data
    draggedStopData = {
      stopSlug: this.dataset.stopSlug,
      stopName: this.dataset.stopName,
      routeSlug: this.dataset.routeSlug,
      routeName: this.dataset.routeName,
    };

    // Set drag data
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", this.innerHTML);

    // Add dragging class for visual feedback
    this.classList.add("dragging");

    // Make all drop zones visible
    document.querySelectorAll(".drop-zone").forEach((zone) => {
      zone.classList.add("drag-active");
    });
  }

  /**
   * Handle drag end event
   */
  function handleDragEnd(e) {
    this.classList.remove("dragging");

    // Remove drag-active class from all drop zones
    document.querySelectorAll(".drop-zone").forEach((zone) => {
      zone.classList.remove("drag-active", "drag-over");
    });

    draggedElement = null;
    draggedStopData = null;
  }

  /**
   * Handle drag over event (required to allow dropping)
   */
  function handleDragOver(e) {
    if (e.preventDefault) {
      e.preventDefault();
    }
    e.dataTransfer.dropEffect = "move";
    return false;
  }

  /**
   * Handle drag enter event
   */
  function handleDragEnter(e) {
    const targetRouteSlug = this.dataset.routeSlug;

    // Only add visual feedback if dragging to a different route
    if (draggedStopData && targetRouteSlug !== draggedStopData.routeSlug) {
      this.classList.add("drag-over");
    }
  }

  /**
   * Handle drag leave event
   */
  function handleDragLeave(e) {
    // Check if we're actually leaving the drop zone (not just a child element)
    if (e.target === this) {
      this.classList.remove("drag-over");
    }
  }

  /**
   * Handle drop event
   */
  function handleDrop(e) {
    if (e.stopPropagation) {
      e.stopPropagation();
    }
    e.preventDefault();

    this.classList.remove("drag-over");

    const targetRouteSlug = this.dataset.routeSlug;

    // Check if dropping on the same route
    if (!draggedStopData || targetRouteSlug === draggedStopData.routeSlug) {
      showNotification("Cannot drop a stop onto its current route.", "warning");
      return false;
    }

    // Get target route name from the route card
    const targetRouteCard = document.querySelector(
      `.route-card[data-route-slug="${targetRouteSlug}"]`
    );
    const targetRouteName = targetRouteCard
      ? targetRouteCard.querySelector(".route-name").textContent.trim()
      : "Unknown Route";

    // Show confirmation modal instead of confirm dialog
    showTransferConfirmModal(draggedStopData, targetRouteSlug, targetRouteName);

    return false;
  }

  /**
   * Show the Bootstrap modal for transfer confirmation
   */
  function showTransferConfirmModal(
    stopData,
    targetRouteSlug,
    targetRouteName
  ) {
    // Store the pending transfer data
    pendingTransfer = {
      stopSlug: stopData.stopSlug,
      targetRouteSlug: targetRouteSlug,
    };

    // Update modal content
    document.getElementById("modal-stop-name").textContent = stopData.stopName;
    document.getElementById("modal-from-route").textContent =
      stopData.routeName;
    document.getElementById("modal-to-route").textContent = targetRouteName;

    // Show the modal
    const modal = new bootstrap.Modal(
      document.getElementById("transferConfirmModal")
    );
    modal.show();
  }

  /**
   * Handle modal confirmation button click
   */
  function handleModalConfirm() {
    if (pendingTransfer) {
      // Close the modal
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("transferConfirmModal")
      );
      modal.hide();

      // Perform the transfer
      performTransfer(
        pendingTransfer.stopSlug,
        pendingTransfer.targetRouteSlug
      );

      // Clear pending transfer
      pendingTransfer = null;
    }
  }

  /**
   * Handle click on "Add Stop" button
   */
  function handleAddStopClick(e) {
    e.preventDefault();

    const button = this;
    const routeSlug = button.dataset.routeSlug;
    const routeName = button.dataset.routeName;

    // Store route data
    pendingAddStop = {
      routeSlug: routeSlug,
      routeName: routeName,
    };

    // Update modal content
    document.getElementById("add-stop-route-name").textContent = routeName;

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById("addStopModal"));
    modal.show();

    // Focus on input after modal is shown
    setTimeout(() => {
      document.getElementById("stopNameInput").focus();
    }, 500);
  }

  /**
   * Handle add stop confirmation
   */
  function handleAddStopConfirm() {
    if (!pendingAddStop) {
      return;
    }

    const stopNameInput = document.getElementById("stopNameInput");
    const stopName = stopNameInput.value.trim();

    // Validate input
    if (!stopName || stopName.length < 2) {
      stopNameInput.classList.add("is-invalid");
      document.getElementById("stopNameError").textContent =
        "Stop name must be at least 2 characters";
      stopNameInput.focus();
      return;
    }

    if (stopName.length > 200) {
      stopNameInput.classList.add("is-invalid");
      document.getElementById("stopNameError").textContent =
        "Stop name cannot exceed 200 characters";
      stopNameInput.focus();
      return;
    }

    // Close the modal
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("addStopModal")
    );
    modal.hide();

    // Create the stop
    createStop(pendingAddStop.routeSlug, stopName);

    // Clear pending data
    pendingAddStop = null;
  }

  /**
   * Create a new stop via API
   */
  function createStop(routeSlug, stopName) {
    // Show loading state
    showLoading(true);

    fetch(ADD_STOP_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        route_slug: routeSlug,
        stop_name: stopName,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);

        if (data.success) {
          showNotification(data.message, "success");

          // Add the new stop to the UI
          addStopToUI(data.stop);
        } else {
          showNotification(data.message, "danger");
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while creating the stop. Please try again.",
          "danger"
        );
        console.error("Create stop error:", error);
      });
  }

  /**
   * Add a newly created stop to the UI
   */
  function addStopToUI(stopData) {
    const routeSlug = stopData.route_slug;
    const routeCard = document.querySelector(
      `.route-card[data-route-slug="${routeSlug}"]`
    );

    if (!routeCard) {
      return;
    }

    const stopsContainer = routeCard.querySelector(".stops-container");

    // Remove empty message if it exists
    const emptyMessage = stopsContainer.querySelector(".empty-route-message");
    if (emptyMessage) {
      emptyMessage.remove();
    }
    
    // Remove delete route button if it exists (route is no longer empty)
    const deleteRouteBtn = routeCard.querySelector(".delete-route-btn");
    if (deleteRouteBtn) {
      deleteRouteBtn.remove();
    }

    // Create new stop element
    const stopElement = document.createElement("div");
    stopElement.className = "stop-item";
    stopElement.draggable = true;
    stopElement.dataset.stopSlug = stopData.slug;
    stopElement.dataset.stopName = stopData.name;
    stopElement.dataset.routeSlug = stopData.route_slug;
    stopElement.dataset.routeName = stopData.route_name;
    stopElement.dataset.pickupCount = stopData.pickup_count;
    stopElement.dataset.dropCount = stopData.drop_count;

    stopElement.innerHTML = `
            <div class="stop-content">
                <div class="stop-drag-handle">
                    <i class="fa-solid fa-grip-vertical"></i>
                </div>
                <div class="stop-info">
                    <div class="stop-name" title="Double-click to edit">${stopData.name}</div>
                    <div class="stop-stats">
                        <span class="badge bg-success me-1">
                            <i class="fas fa-arrow-up"></i> ${stopData.pickup_count}
                        </span>
                        <span class="badge bg-info">
                            <i class="fas fa-arrow-down"></i> ${stopData.drop_count}
                        </span>
                        <button class="btn btn-sm btn-outline-danger delete-stop-btn ms-2" 
                                draggable="false"
                                data-stop-slug="${stopData.slug}"
                                data-stop-name="${stopData.name}"
                                data-route-name="${stopData.route_name}"
                                title="Delete this stop">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

    // Add to container
    stopsContainer.appendChild(stopElement);

    // Setup drag events
    stopElement.addEventListener("dragstart", handleDragStart);
    stopElement.addEventListener("dragend", handleDragEnd);

    // Setup inline editing
    const stopNameElement = stopElement.querySelector(".stop-name");
    if (stopNameElement) {
      stopNameElement.addEventListener("dblclick", handleStopNameEdit);
    }
    
    // Setup delete button
    const deleteButton = stopElement.querySelector(".delete-stop-btn");
    if (deleteButton) {
      deleteButton.addEventListener("click", handleDeleteStopClick);
    }

    // Update stop count
    const currentCount = parseInt(
      routeCard.querySelector(".stop-count").textContent
    );
    updateStopCount(routeSlug, currentCount + 1);
  }

  /**
   * Perform the actual transfer via AJAX
   */
  function performTransfer(stopSlug, targetRouteSlug) {
    // Show loading overlay
    showLoading(true);

    fetch(TRANSFER_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        stop_slug: stopSlug,
        target_route_slug: targetRouteSlug,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);

        if (data.success) {
          showNotification(data.message, "success");

          // Update the UI
          updateUIAfterTransfer(data);
        } else {
          showNotification(data.message, "danger");
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while transferring the stop. Please try again.",
          "danger"
        );
        console.error("Transfer error:", error);
      });
  }

  /**
   * Update the UI after successful transfer
   */
  function updateUIAfterTransfer(data) {
    const stopSlug = data.stop.slug;
    const sourceRouteSlug = data.source_route.slug;
    const targetRouteSlug = data.target_route.slug;

    // Find and move the stop element
    const stopElement = document.querySelector(
      `.stop-item[data-stop-slug="${stopSlug}"]`
    );
    const targetDropZone = document.querySelector(
      `.drop-zone[data-route-slug="${targetRouteSlug}"]`
    );
    const targetStopsContainer =
      targetDropZone.querySelector(".stops-container");

    if (stopElement && targetStopsContainer) {
      // Update stop's data attributes
      stopElement.dataset.routeSlug = targetRouteSlug;
      stopElement.dataset.routeName = data.stop.new_route_name;

      // Remove empty message from target if it exists
      const emptyMessage = targetStopsContainer.querySelector(
        ".empty-route-message"
      );
      if (emptyMessage) {
        emptyMessage.remove();
      }

      // Move the element
      targetStopsContainer.appendChild(stopElement);

      // Update stop counts
      updateStopCount(sourceRouteSlug, data.source_route.stop_count);
      updateStopCount(targetRouteSlug, data.target_route.stop_count);

      // Check if source route is now empty
      const sourceStopsContainer = document.querySelector(
        `.route-card[data-route-slug="${sourceRouteSlug}"] .stops-container`
      );
      if (sourceStopsContainer && sourceStopsContainer.children.length === 0) {
        sourceStopsContainer.innerHTML = `
                    <div class="empty-route-message">
                        <i class="fa-solid fa-inbox me-2"></i>No stops in this route
                    </div>
                `;
      }

      // Re-initialize drag events for the moved element
      stopElement.addEventListener("dragstart", handleDragStart);
      stopElement.addEventListener("dragend", handleDragEnd);

      // Re-initialize inline editing for the stop name
      const stopNameElement = stopElement.querySelector(".stop-name");
      if (stopNameElement) {
        stopNameElement.addEventListener("dblclick", handleStopNameEdit);
      }
    }
  }

  /**
   * Update the stop count display for a route
   */
  function updateStopCount(routeSlug, count) {
    const routeCard = document.querySelector(
      `.route-card[data-route-slug="${routeSlug}"]`
    );
    if (routeCard) {
      const stopCountElement = routeCard.querySelector(".stop-count");
      if (stopCountElement) {
        stopCountElement.textContent = count;

        // Update pluralization
        const parentText = stopCountElement.parentNode;
        const pluralText = count === 1 ? " stop" : " stops";
        parentText.childNodes.forEach((node) => {
          if (node.nodeType === 3 && node.textContent.includes("stop")) {
            node.textContent = pluralText;
          }
        });
      }
    }
  }

  /**
   * Show notification message
   */
  function showNotification(message, type = "info") {
    const notification = document.getElementById("transfer-notification");
    const messageElement = document.getElementById("notification-message");

    if (notification && messageElement) {
      // Remove existing alert classes
      notification.className = "alert alert-dismissible fade show";

      // Add new type class
      notification.classList.add(`alert-${type}`);

      // Set message
      messageElement.textContent = message;

      // Show notification
      notification.style.display = "block";

      // Auto-hide after 5 seconds for non-error messages
      if (type !== "danger") {
        setTimeout(() => {
          const bsAlert = new bootstrap.Alert(notification);
          bsAlert.close();
        }, 5000);
      }
    }
  }

  /**
   * Show/hide loading overlay
   */
  function showLoading(show) {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.display = show ? "flex" : "none";
    }
  }

  /**
   * Handle click on delete stop button
   */
  function handleDeleteStopClick(e) {
    console.log("Delete button clicked!");
    e.preventDefault();
    e.stopPropagation(); // Prevent dragging when clicking delete
    
    const button = e.currentTarget;
    const stopSlug = button.dataset.stopSlug;
    const stopName = button.dataset.stopName;
    const routeName = button.dataset.routeName;
    
    console.log("Stop data:", { stopSlug, stopName, routeName });
    
    // Store stop data
    pendingDeleteStop = {
      stopSlug: stopSlug,
      stopName: stopName,
      routeName: routeName
    };
    
    // Update modal content
    const deleteStopNameEl = document.getElementById("delete-stop-name");
    const deleteRouteNameEl = document.getElementById("delete-route-name");
    
    console.log("Modal elements found:", { deleteStopNameEl, deleteRouteNameEl });
    
    if (deleteStopNameEl) deleteStopNameEl.textContent = stopName;
    if (deleteRouteNameEl) deleteRouteNameEl.textContent = routeName;
    
    // Show the modal
    const modalElement = document.getElementById("deleteStopModal");
    console.log("Modal element:", modalElement);
    console.log("Bootstrap available:", typeof bootstrap !== 'undefined');
    
    if (modalElement) {
      if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        try {
          // Try to get existing modal instance or create new one
          let modal = bootstrap.Modal.getInstance(modalElement);
          if (!modal) {
            modal = new bootstrap.Modal(modalElement);
          }
          console.log("Modal instance created:", modal);
          modal.show();
        } catch (error) {
          console.error("Error showing modal:", error);
          // Fallback: try using jQuery if available
          if (typeof $ !== 'undefined') {
            console.log("Trying jQuery fallback");
            $(modalElement).modal('show');
          }
        }
      } else {
        console.error("Bootstrap Modal is not available!");
        // Try direct manipulation as last resort
        modalElement.classList.add('show');
        modalElement.style.display = 'block';
        document.body.classList.add('modal-open');
      }
    } else {
      console.error("Modal element not found!");
    }
  }

  /**
   * Handle delete stop confirmation
   */
  function handleDeleteStopConfirm() {
    if (!pendingDeleteStop) {
      return;
    }
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById("deleteStopModal"));
    modal.hide();
    
    // Delete the stop
    deleteStop(pendingDeleteStop.stopSlug);
    
    // Clear pending data
    pendingDeleteStop = null;
  }

  /**
   * Delete a stop via API
   */
  function deleteStop(stopSlug) {
    // Show loading state
    showLoading(true);
    
    fetch(DELETE_STOP_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        stop_slug: stopSlug,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);
        
        if (data.success) {
          showNotification(data.message, "success");
          
          // Remove the stop from the UI
          removeStopFromUI(data.stop);
        } else {
          showNotification(data.message, "danger");
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while deleting the stop. Please try again.",
          "danger"
        );
        console.error("Delete stop error:", error);
      });
  }

  /**
   * Remove a deleted stop from the UI
   */
  function removeStopFromUI(stopData) {
    const routeSlug = stopData.route_slug;
    const stopSlug = stopData.slug;
    const routeCard = document.querySelector(`.route-card[data-route-slug="${routeSlug}"]`);
    
    if (!routeCard) {
      return;
    }
    
    // Find and remove the stop element
    const stopElement = routeCard.querySelector(`.stop-item[data-stop-slug="${stopSlug}"]`);
    if (stopElement) {
      stopElement.remove();
    }
    
    // Check if route is now empty
    const stopsContainer = routeCard.querySelector(".stops-container");
    if (stopsContainer && stopsContainer.children.length === 0) {
      stopsContainer.innerHTML = `
        <div class="empty-route-message">
          <i class="fa-solid fa-inbox me-2"></i>No stops in this route
        </div>
      `;
      
      // Add delete route button if route is now empty
      const addStopBtn = routeCard.querySelector('.add-stop-btn');
      if (addStopBtn && !routeCard.querySelector('.delete-route-btn')) {
        const routeName = routeCard.querySelector('.route-name').textContent.trim();
        const deleteRouteBtn = document.createElement('button');
        deleteRouteBtn.className = 'btn btn-sm btn-outline-light delete-route-btn';
        deleteRouteBtn.setAttribute('data-route-slug', routeSlug);
        deleteRouteBtn.setAttribute('data-route-name', routeName);
        deleteRouteBtn.setAttribute('title', 'Delete this route');
        deleteRouteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        deleteRouteBtn.addEventListener('click', handleDeleteRouteClick);
        addStopBtn.parentElement.appendChild(deleteRouteBtn);
      }
    }
    
    // Update stop count
    const currentCount = parseInt(routeCard.querySelector(".stop-count").textContent);
    updateStopCount(routeSlug, currentCount - 1);
  }

  /**
   * Handle create route button click
   */
  function handleCreateRouteClick(e) {
    e.preventDefault();
    
    // Show the modal
    const modalElement = document.getElementById("createRouteModal");
    if (modalElement) {
      if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        try {
          let modal = bootstrap.Modal.getInstance(modalElement);
          if (!modal) {
            modal = new bootstrap.Modal(modalElement);
          }
          modal.show();
        } catch (error) {
          console.error("Error showing create route modal:", error);
        }
      }
    }
  }

  /**
   * Handle create route confirmation
   */
  function handleCreateRouteConfirm() {
    const routeNameInput = document.getElementById("routeNameInput");
    const routeName = routeNameInput.value.trim();
    
    if (!routeName) {
      routeNameInput.classList.add("is-invalid");
      return;
    }
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById("createRouteModal"));
    modal.hide();
    
    // Create the route
    createRoute(routeName);
  }

  /**
   * Create a new route via API
   */
  function createRoute(routeName) {
    showLoading(true);
    
    fetch(CREATE_ROUTE_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        route_name: routeName,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);
        
        if (data.success) {
          showNotification(data.message, "success");
          
          // Add the route to the UI
          addRouteToUI(data.route);
        } else {
          showNotification(data.message, "danger");
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while creating the route. Please try again.",
          "danger"
        );
        console.error("Create route error:", error);
      });
  }

  /**
   * Add a newly created route to the UI
   */
  function addRouteToUI(routeData) {
    const routesGrid = document.querySelector(".routes-grid");
    
    if (!routesGrid) {
      // If no routes grid exists, reload the page to show the new route
      window.location.reload();
      return;
    }
    
    // Create route card element
    const routeCard = document.createElement("div");
    routeCard.className = "route-card";
    routeCard.dataset.routeSlug = routeData.slug;
    
    routeCard.innerHTML = `
      <div class="route-header">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <h5 class="route-name mb-1">${routeData.name}</h5>
            <small class="text-muted">
              <span class="stop-count">0</span> stops
            </small>
          </div>
          <div class="d-flex gap-2">
            <button class="btn btn-sm btn-light add-stop-btn" 
                    data-route-slug="${routeData.slug}"
                    data-route-name="${routeData.name}"
                    title="Add new stop to this route">
              <i class="fa-solid fa-plus me-1"></i>Add Stop
            </button>
            <button class="btn btn-sm btn-outline-light delete-route-btn" 
                    data-route-slug="${routeData.slug}"
                    data-route-name="${routeData.name}"
                    title="Delete this route">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
      <div class="drop-zone" data-route-slug="${routeData.slug}">
        <div class="stops-container">
          <div class="empty-route-message">
            <i class="fa-solid fa-inbox me-2"></i>No stops in this route
          </div>
        </div>
        <div class="drop-zone-placeholder">Drop stop here</div>
      </div>
    `;
    
    // Add to grid
    routesGrid.appendChild(routeCard);
    
    // Setup event listeners
    const dropZone = routeCard.querySelector(".drop-zone");
    dropZone.addEventListener("dragover", handleDragOver);
    dropZone.addEventListener("dragenter", handleDragEnter);
    dropZone.addEventListener("dragleave", handleDragLeave);
    dropZone.addEventListener("drop", handleDrop);
    
    const addStopBtn = routeCard.querySelector(".add-stop-btn");
    addStopBtn.addEventListener("click", handleAddStopClick);
    
    const deleteRouteBtn = routeCard.querySelector(".delete-route-btn");
    deleteRouteBtn.addEventListener("click", handleDeleteRouteClick);
  }

  /**
   * Handle delete route button click
   */
  function handleDeleteRouteClick(e) {
    console.log("Delete route button clicked!");
    e.preventDefault();
    e.stopPropagation();
    
    const button = e.currentTarget;
    const routeSlug = button.dataset.routeSlug;
    const routeName = button.dataset.routeName;
    
    console.log("Route data:", { routeSlug, routeName });
    
    // Store route data
    pendingDeleteRoute = {
      routeSlug: routeSlug,
      routeName: routeName
    };
    
    // Update modal content
    const deleteRouteNameEl = document.getElementById("delete-route-name-display");
    if (deleteRouteNameEl) deleteRouteNameEl.textContent = routeName;
    
    // Show the modal
    const modalElement = document.getElementById("deleteRouteModal");
    if (modalElement) {
      if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        try {
          let modal = bootstrap.Modal.getInstance(modalElement);
          if (!modal) {
            modal = new bootstrap.Modal(modalElement);
          }
          console.log("Modal instance created:", modal);
          modal.show();
        } catch (error) {
          console.error("Error showing modal:", error);
        }
      }
    }
  }

  /**
   * Handle delete route confirmation
   */
  function handleDeleteRouteConfirm() {
    if (!pendingDeleteRoute) {
      return;
    }
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById("deleteRouteModal"));
    modal.hide();
    
    // Delete the route
    deleteRoute(pendingDeleteRoute.routeSlug);
    
    // Clear pending data
    pendingDeleteRoute = null;
  }

  /**
   * Delete a route via API
   */
  function deleteRoute(routeSlug) {
    showLoading(true);
    
    fetch(DELETE_ROUTE_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CSRF_TOKEN,
      },
      body: JSON.stringify({
        route_slug: routeSlug,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        showLoading(false);
        
        if (data.success) {
          showNotification(data.message, "success");
          
          // Remove the route from the UI
          removeRouteFromUI(data.route);
        } else {
          showNotification(data.message, "danger");
        }
      })
      .catch((error) => {
        showLoading(false);
        showNotification(
          "An error occurred while deleting the route. Please try again.",
          "danger"
        );
        console.error("Delete route error:", error);
      });
  }

  /**
   * Remove a deleted route from the UI
   */
  function removeRouteFromUI(routeData) {
    const routeCard = document.querySelector(`.route-card[data-route-slug="${routeData.slug}"]`);
    
    if (routeCard) {
      routeCard.remove();
      
      // Check if there are any routes left
      const routesGrid = document.querySelector(".routes-grid");
      if (routesGrid && routesGrid.children.length === 0) {
        // Show empty state or reload page
        window.location.reload();
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
