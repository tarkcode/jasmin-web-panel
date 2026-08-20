(function($){
    var local_path = window.location.pathname, csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    var collectionlist_check = function(){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "list" },
            success: function(data){
                var datalist = data["ips"] || [];
                var output = $.map(datalist, function(val, i){
                    return `<tr>
                        <td>${i+1}</td>
                        <td><strong>${esc(val.ip)}</strong></td>
                        <td>${esc(val.label) || '<span class="text-muted">—</span>'}</td>
                        <td class="text-center" style="padding-top:4px;padding-bottom:4px;">
                            <a href="javascript:void(0)" class="btn btn-light btn-sm" title="Remove" onclick="return remove_ip('${esc(val.ip)}');"><i class="fas fa-trash"></i></a>
                        </td>
                    </tr>`;
                });
                $("#collectionlist").html(datalist.length > 0 ? output : $(".isEmpty").html());
                if (data.writable === false) {
                    toastr.warning("Whitelist file is not writable by the panel — check the /opt/jasmin-fw mount.", {timeOut: 8000});
                }
            }, error: function(jqXHR){ quick_display_modal_error(jqXHR.responseText); }
        });
    };
    collectionlist_check();

    window.remove_ip = function(ip){
        sweetAlert({
            title: global_trans["areyousuretodelete"],
            text: "Remove " + ip + " from the SMPP whitelist?",
            type: 'warning', showCancelButton: true,
            cancelButtonClass: "btn btn-secondary m-btn m-btn--pill m-btn--icon",
            cancelButtonText: global_trans["no"],
            confirmButtonClass: "btn btn-danger m-btn m-btn--pill m-btn--air m-btn--icon",
            confirmButtonText: global_trans["yes"],
        }, function(isConfirm){
            if (!isConfirm) return;
            $.ajax({ type: "POST", url: local_path + 'manage/', data: { csrfmiddlewaretoken: csrf, s: "delete", ip: ip },
                success: function(data){ toastr.success(data["message"], {closeButton:true, progressBar:true}); collectionlist_check(); },
                error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton:true, progressBar:true}); }
            });
        });
    };

    $("#add_new_obj").on('click', function(){
        $("#add_modal_form")[0].reset();
        $("#collection_modal").modal("show");
    });
    $("#add_modal_form").on("submit", function(e){
        e.preventDefault();
        var inputs = $(this).find("input, button");
        $.ajax({ type: "POST", url: $(this).attr("action"), data: $(this).serialize(),
            beforeSend: function(){ inputs.prop("disabled", true); },
            success: function(data){
                toastr.success(data["message"], {closeButton:true, progressBar:true});
                inputs.prop("disabled", false);
                $(".modal").modal("hide");
                collectionlist_check();
            },
            error: function(jqXHR){
                inputs.prop("disabled", false);
                toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton:true, progressBar:true});
            }
        });
    });
    $("li.nav-item.smpp_access-menu").addClass("active");
})(jQuery);
