$(document).ready(function() {
    
    $('form.needs-validation').on('submit', function(event) {
        if (!this.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    
    $("#search-topic").on("keyup", function() {
        let topic = $(this).val();
        if (topic.length > 2) {
            $.post("/search", { topic: topic }, function(data) {
                let results = $("#search-results");
                results.empty();
                data.content.forEach(item => {
                    results.append(`
                        <div class="card mb-2 shadow-sm animate__animated animate__fadeIn">
                            <div class="card-body">
                                <h5 class="card-title">${item.title}</h5>
                                <p class="card-text">${item.body}</p>
                            </div>
                        </div>
                    `);
                });
            }).fail(function(xhr, status, error) {
                console.log("Search error: " + error);
            });
        }
    });
});
