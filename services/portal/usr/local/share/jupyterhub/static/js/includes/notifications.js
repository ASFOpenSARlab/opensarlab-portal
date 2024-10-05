function notifications(lab, profile) {

    require.config({paths: {toastr: "https://cdnjs.cloudflare.com/ajax/libs/toastr.js/2.1.4/toastr.min"}});

    require([
        'jquery',
        'toastr'
    ], function ($, toastr) {

        toastr.options = {
            "closeButton": true,
            "newestOnTop": true,
            "progressBar": true,
            "preventDuplicates": false,
            "onclick": null,
            "showDuration": "30",
            "hideDuration": "10",
            "timeOut": "0",
            "extendedTimeOut": "0",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        }

        fetch(window.location.origin + '/user/notifications/'+encodeURIComponent(lab)+'?profile='+encodeURIComponent(profile) )
            .then( response => response.json() )
            .then( notes => {
                console.log(notes)
                notes.forEach( (entry) => {
                    toastr.options.positionClass = "toast-"+entry["placement"]
                    toastr[entry['type']](entry['message'], entry['title'])
                })
            })
            .catch( error => console.log(error) )
    })
}