// This script assumes you have linked jQuery: <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

$(document).ready(function() {

    // Handler for clicking any row in the table
    $('.clickable-row').on('click', function() {

        var eventId = $(this).data('event-id');

        // 1. Manage Visual State
        $('.clickable-row').removeClass('selected');
        $(this).addClass('selected');

        // 2. Hide placeholder and show loading state in content area
        $('#initial-details-message').hide();
        var detailsContent = $('#event-details-content').show().html(
            `<p class="text-center" style="color: var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> Loading details...</p>`
        );


        // --- NOTE: You would replace the placeholder below with an AJAX call to your Django backend ---
        // Example Django AJAX call:
        /*
        $.ajax({
            url: `/events/${eventId}/get_details_html/`,
            method: 'GET',
            success: function(data) {
                detailsContent.html(data.html_content);
            },
            error: function() {
                detailsContent.html('<div style="color: var(--danger-color);">Error loading event details.</div>');
            }
        });
        */

        // --- Placeholder Content for Immediate Testing ---
        var eventName = $(this).find('td[data-label="Event Name"]').text();
        var eventDate = $(this).find('td[data-label="Date"]').text();

        var demoHtml = `
            <h4 style="color: var(--primary-color);">${eventName} (ID: ${eventId})</h4>
            <p style="margin-bottom: 5px;"><strong>Date:</strong> ${eventDate}</p>
            <p style="margin-bottom: 5px;"><strong>Registrations:</strong> ${$(this).find('td[data-label="Registrations"]').text()}</p>
            <p><strong>Status:</strong> ${$(this).find('td[data-label="Status"]').text()}</p>
            <hr style="border-color: var(--border-color);">
            <p style="color: var(--text-muted); font-size: 0.85rem;">Event description and full details appear here.</p>
            <button class="btn btn-sm btn-info w-100 mb-2" style="background-color: var(--secondary-color); color: var(--background-dark); border: none;" onclick="alert('Viewing Registrants for ${eventName}')">
                <i class="fas fa-users"></i> View Registrants
            </button>
            <button class="btn btn-sm btn-warning w-100" style="background-color: var(--warning-color); color: var(--background-dark); border: none;" onclick="alert('Editing ${eventName}')">
                <i class="fas fa-edit"></i> Full Edit Form
            </button>
        `;
        detailsContent.html(demoHtml);
        // --- End Placeholder ---
    });
});