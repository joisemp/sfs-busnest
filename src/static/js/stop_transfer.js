/**
 * stop_transfer.js - Drag and Drop functionality for transferring stops between routes
 * 
 * This script handles the HTML5 drag-and-drop interface for moving stops from one route to another.
 * It communicates with the backend API to perform the actual transfer and updates the UI accordingly.
 * Also includes inline editing functionality for stop names.
 */

(function() {
    'use strict';

    // State management
    let draggedElement = null;
    let draggedStopData = null;
    let editingElement = null;
    let pendingTransfer = null; // Store pending transfer data for modal confirmation

    /**
     * Initialize drag-and-drop and inline editing functionality
     */
    function init() {
        const stopItems = document.querySelectorAll('.stop-item');
        const dropZones = document.querySelectorAll('.drop-zone');

        // Setup drag events for all stops
        stopItems.forEach(stop => {
            stop.addEventListener('dragstart', handleDragStart);
            stop.addEventListener('dragend', handleDragEnd);
            
            // Setup inline editing on stop names
            const stopNameElement = stop.querySelector('.stop-name');
            if (stopNameElement) {
                stopNameElement.addEventListener('dblclick', handleStopNameEdit);
            }
        });

        // Setup drop zones
        dropZones.forEach(zone => {
            zone.addEventListener('dragover', handleDragOver);
            zone.addEventListener('dragenter', handleDragEnter);
            zone.addEventListener('dragleave', handleDragLeave);
            zone.addEventListener('drop', handleDrop);
        });
        
        // Setup modal confirm button
        const confirmBtn = document.getElementById('confirmTransferBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', handleModalConfirm);
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
        const stopItem = stopNameElement.closest('.stop-item');
        const currentName = stopNameElement.textContent.trim();
        const stopSlug = stopItem.dataset.stopSlug;
        
        // Create input field
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'stop-name-input';
        input.value = currentName;
        input.maxLength = 200;
        
        // Store reference
        editingElement = stopNameElement;
        
        // Replace text with input
        stopNameElement.style.display = 'none';
        stopNameElement.parentNode.insertBefore(input, stopNameElement);
        
        // Focus and select text
        input.focus();
        input.select();
        
        // Handle save on Enter key
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveStopName(stopSlug, input.value.trim(), stopNameElement, input);
            } else if (e.key === 'Escape') {
                cancelEdit(stopNameElement, input);
            }
        });
        
        // Handle save on blur (clicking outside)
        input.addEventListener('blur', function() {
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
            showNotification('Stop name must be at least 2 characters', 'warning');
            inputElement.focus();
            return;
        }
        
        // Show loading state
        showLoading(true);
        
        fetch(UPDATE_STOP_NAME_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({
                stop_slug: stopSlug,
                new_name: newName
            })
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            
            if (data.success) {
                // Update the stop name in the DOM
                stopNameElement.textContent = data.stop.name;
                stopNameElement.style.display = '';
                inputElement.remove();
                editingElement = null;
                
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'danger');
                inputElement.focus();
            }
        })
        .catch(error => {
            showLoading(false);
            showNotification('An error occurred while updating the stop name. Please try again.', 'danger');
            console.error('Update stop name error:', error);
            inputElement.focus();
        });
    }

    /**
     * Cancel editing and restore original state
     */
    function cancelEdit(stopNameElement, inputElement) {
        stopNameElement.style.display = '';
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
        
        draggedElement = this;
        
        // Store stop data
        draggedStopData = {
            stopSlug: this.dataset.stopSlug,
            stopName: this.dataset.stopName,
            routeSlug: this.dataset.routeSlug,
            routeName: this.dataset.routeName
        };

        // Set drag data
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.innerHTML);

        // Add dragging class for visual feedback
        this.classList.add('dragging');

        // Make all drop zones visible
        document.querySelectorAll('.drop-zone').forEach(zone => {
            zone.classList.add('drag-active');
        });
    }

    /**
     * Handle drag end event
     */
    function handleDragEnd(e) {
        this.classList.remove('dragging');
        
        // Remove drag-active class from all drop zones
        document.querySelectorAll('.drop-zone').forEach(zone => {
            zone.classList.remove('drag-active', 'drag-over');
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
        e.dataTransfer.dropEffect = 'move';
        return false;
    }

    /**
     * Handle drag enter event
     */
    function handleDragEnter(e) {
        const targetRouteSlug = this.dataset.routeSlug;
        
        // Only add visual feedback if dragging to a different route
        if (draggedStopData && targetRouteSlug !== draggedStopData.routeSlug) {
            this.classList.add('drag-over');
        }
    }

    /**
     * Handle drag leave event
     */
    function handleDragLeave(e) {
        // Check if we're actually leaving the drop zone (not just a child element)
        if (e.target === this) {
            this.classList.remove('drag-over');
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

        this.classList.remove('drag-over');

        const targetRouteSlug = this.dataset.routeSlug;

        // Check if dropping on the same route
        if (!draggedStopData || targetRouteSlug === draggedStopData.routeSlug) {
            showNotification('Cannot drop a stop onto its current route.', 'warning');
            return false;
        }

        // Get target route name from the route card
        const targetRouteCard = document.querySelector(`.route-card[data-route-slug="${targetRouteSlug}"]`);
        const targetRouteName = targetRouteCard ? targetRouteCard.querySelector('.route-name').textContent.trim() : 'Unknown Route';

        // Show confirmation modal instead of confirm dialog
        showTransferConfirmModal(draggedStopData, targetRouteSlug, targetRouteName);

        return false;
    }

    /**
     * Show the Bootstrap modal for transfer confirmation
     */
    function showTransferConfirmModal(stopData, targetRouteSlug, targetRouteName) {
        // Store the pending transfer data
        pendingTransfer = {
            stopSlug: stopData.stopSlug,
            targetRouteSlug: targetRouteSlug
        };

        // Update modal content
        document.getElementById('modal-stop-name').textContent = stopData.stopName;
        document.getElementById('modal-from-route').textContent = stopData.routeName;
        document.getElementById('modal-to-route').textContent = targetRouteName;

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('transferConfirmModal'));
        modal.show();
    }

    /**
     * Handle modal confirmation button click
     */
    function handleModalConfirm() {
        if (pendingTransfer) {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('transferConfirmModal'));
            modal.hide();

            // Perform the transfer
            performTransfer(pendingTransfer.stopSlug, pendingTransfer.targetRouteSlug);

            // Clear pending transfer
            pendingTransfer = null;
        }
    }

    /**
     * Perform the actual transfer via AJAX
     */
    function performTransfer(stopSlug, targetRouteSlug) {
        // Show loading overlay
        showLoading(true);

        fetch(TRANSFER_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({
                stop_slug: stopSlug,
                target_route_slug: targetRouteSlug
            })
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            
            if (data.success) {
                showNotification(data.message, 'success');
                
                // Update the UI
                updateUIAfterTransfer(data);
            } else {
                showNotification(data.message, 'danger');
            }
        })
        .catch(error => {
            showLoading(false);
            showNotification('An error occurred while transferring the stop. Please try again.', 'danger');
            console.error('Transfer error:', error);
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
        const stopElement = document.querySelector(`.stop-item[data-stop-slug="${stopSlug}"]`);
        const targetDropZone = document.querySelector(`.drop-zone[data-route-slug="${targetRouteSlug}"]`);
        const targetStopsContainer = targetDropZone.querySelector('.stops-container');

        if (stopElement && targetStopsContainer) {
            // Update stop's data attributes
            stopElement.dataset.routeSlug = targetRouteSlug;
            stopElement.dataset.routeName = data.stop.new_route_name;

            // Remove empty message from target if it exists
            const emptyMessage = targetStopsContainer.querySelector('.empty-route-message');
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
            stopElement.addEventListener('dragstart', handleDragStart);
            stopElement.addEventListener('dragend', handleDragEnd);
            
            // Re-initialize inline editing for the stop name
            const stopNameElement = stopElement.querySelector('.stop-name');
            if (stopNameElement) {
                stopNameElement.addEventListener('dblclick', handleStopNameEdit);
            }
        }
    }

    /**
     * Update the stop count display for a route
     */
    function updateStopCount(routeSlug, count) {
        const routeCard = document.querySelector(`.route-card[data-route-slug="${routeSlug}"]`);
        if (routeCard) {
            const stopCountElement = routeCard.querySelector('.stop-count');
            if (stopCountElement) {
                stopCountElement.textContent = count;
                
                // Update pluralization
                const parentText = stopCountElement.parentNode;
                const pluralText = count === 1 ? ' stop' : ' stops';
                parentText.childNodes.forEach(node => {
                    if (node.nodeType === 3 && node.textContent.includes('stop')) {
                        node.textContent = pluralText;
                    }
                });
            }
        }
    }

    /**
     * Show notification message
     */
    function showNotification(message, type = 'info') {
        const notification = document.getElementById('transfer-notification');
        const messageElement = document.getElementById('notification-message');
        
        if (notification && messageElement) {
            // Remove existing alert classes
            notification.className = 'alert alert-dismissible fade show';
            
            // Add new type class
            notification.classList.add(`alert-${type}`);
            
            // Set message
            messageElement.textContent = message;
            
            // Show notification
            notification.style.display = 'block';
            
            // Auto-hide after 5 seconds for non-error messages
            if (type !== 'danger') {
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
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
