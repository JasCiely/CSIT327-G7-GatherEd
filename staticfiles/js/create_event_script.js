$(document).ready(function() {
    // Check if jQuery is loaded
    if (typeof jQuery === 'undefined') {
        console.error("jQuery is not loaded. AJAX submission will not work.");
        return;
    }

    // --- Pop-up Notification Function (Assumes Bootstrap is loaded) ---
    function showNotification(message, type) {
        // 'type' will be 'success' or 'danger'
        const notificationArea = $('#notification-area');

        // This is Bootstrap's structure for a dismissible alert
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;

        // Clear previous messages, insert new HTML, and fade in
        notificationArea.html(alertHtml).hide().fadeIn(500);

        // Auto-close the message after 4 seconds
        setTimeout(function() {
            // Find the alert and trigger the Bootstrap close behavior
            notificationArea.find('.alert').alert('close');
        }, 4000);
    }

    // --- AJAX Form Submission Handler ---
    $('#create-event-form').on('submit', function(e) {
        e.preventDefault(); // <-- CRITICAL: Prevents browser redirect

        const form = $(this);
        const url = form.attr('action');
        const data = form.serialize();

        const submitButton = form.find('button[type="submit"]');
        submitButton.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Scheduling...');


        $.ajax({
            url: url,
            type: 'POST',
            data: data,
            dataType: 'json', // Expecting JSON response

            success: function(response) {
                if (response.status === 'success') {
                    showNotification(response.message, 'success');

                    // Clear the form fields on success
                    form[0].reset();
                } else {
                    // Status 200, but logic error from Django view
                    showNotification("Error: " + response.message, 'warning');
                }
            },

            error: function(xhr) {
                // This handles 4xx or 5xx errors
                let errorMessage = "An unexpected server error occurred.";
                try {
                    // Try to get the specific JSON error message
                    if (xhr.responseJSON && xhr.responseJSON.message) {
                        errorMessage = xhr.responseJSON.message;
                    }
                } catch (e) {
                    // Fallback for non-JSON or other errors
                    errorMessage = `Server Error (${xhr.status}): Please fix the Admin Profile (ID 13) or check logs.`;
                }
                showNotification(errorMessage, 'danger');
            },

            complete: function() {
                // Re-enable the button
                submitButton.prop('disabled', false).html('<i class="fas fa-calendar-plus"></i> Schedule Event');
            }
        });
    });
});