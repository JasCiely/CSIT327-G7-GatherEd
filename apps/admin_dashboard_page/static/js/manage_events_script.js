$(document).ready(function() {

    // Use event delegation on the document for elements that might be loaded later via AJAX.
    $(document).on('click', '.clickable-row', function() {

        var eventId = $(this).data('event-id');

        // 1. Manage Visual State
        $('.clickable-row').removeClass('selected');
        $(this).addClass('selected');

        // 2. Hide placeholder and show loading state
        $('#initial-details-message').hide();
        var detailsContent = $('#event-details-content').show().html(
            `<p class="text-center" style="color: var(--text-muted); padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading details...</p>`
        );

        // --- ACTUAL AJAX CALL TO DJANGO BACKEND ---
        $.ajax({
            // Construct the URL using the eventId data attribute
            url: `/manage/event/${eventId}/details/`,
            method: 'GET',
            headers: {
                // IMPORTANT: Tells Django this is an AJAX request
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(data) {
                // data contains the HTML fragment
                detailsContent.html(data);
            },
            error: function(xhr) {
                // Enhanced error reporting
                let errorMsg = xhr.responseText || `Error ${xhr.status}: Failed to load event details.`;
                detailsContent.html(`<div style="color: var(--danger-color); padding: 20px;">${errorMsg}</div>`);
                console.error("AJAX Error details:", xhr);
            }
        });
        // --- END AJAX CALL ---
    });
});