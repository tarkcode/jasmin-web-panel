(function($){
    var local_path = window.location.pathname, csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var add_modal_form = "#add_modal_form", edit_modal_form = "#edit_modal_form";
    var variant_boxes = [add_modal_form, edit_modal_form];
    var ROUTES_DICT = {};
    var CONNECTORS = [];
    var ALL_ROUTES = [];

    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    function statusBadge(val){
        var map = { active: 'badge-success', testing: 'badge-warning', inactive: 'badge-secondary' };
        return '<span class="badge ' + (map[val.status] || 'badge-secondary') + '">' + esc(val.status_display) + '</span>';
    }

    // Populate the connector dropdowns (both modals), keeping any current value.
    function loadConnectors(cb){
        $.ajax({ url: main_trans.url2smppccm, type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "list" },
            success: function(d){
                CONNECTORS = (d.connectors || []).map(function(c){ return c.cid; });
                var opts = CONNECTORS.slice().reverse().map(function(cid){
                    return '<option value="' + esc(cid) + '">' + esc(cid) + '</option>';
                }).join('');
                $(".smpp-connector-select").html(opts || '<option value="">(no connectors)</option>');
                populateProviderFilter();
                if (cb) cb();
            }
        });
    }

    function populateProviderFilter(){
        var current = $("#provider_filter").val();
        // List ALL SMPP providers (connectors), plus any route connector that is
        // no longer in the connector list, so every provider is selectable.
        var providers = CONNECTORS.slice();
        ALL_ROUTES.forEach(function(r){ if (r.smpp_connector && providers.indexOf(r.smpp_connector) === -1) providers.push(r.smpp_connector); });
        providers.sort();
        var opts = '<option value="">All providers</option>' + providers.map(function(p){
            return '<option value="' + esc(p) + '">' + esc(p) + '</option>';
        }).join('');
        $("#provider_filter").html(opts).val(current);
    }

    function renderRoutes(){
        var filter = $("#provider_filter").val() || "";
        var rows = filter ? ALL_ROUTES.filter(function(r){ return r.smpp_connector === filter; }) : ALL_ROUTES;
        ROUTES_DICT = {};
        var output = $.map(rows, function(val, i){
            ROUTES_DICT[i+1] = val;
            return `<tr>
                <td>${i+1}</td>
                <td><strong>${esc(val.name)}</strong></td>
                <td>${esc(val.country) || '<span class="text-muted">—</span>'}</td>
                <td><span class="badge badge-light">${esc(val.route_type_display)}</span></td>
                <td>${esc(val.smpp_connector)}</td>
                <td class="text-right" style="font-variant-numeric:tabular-nums;">${esc(val.buy_price)} <span class="text-muted">${esc(val.currency)}</span></td>
                <td class="text-center">${esc(val.tps)}</td>
                <td class="text-center">${statusBadge(val)}</td>
                <td class="text-center" style="padding-top:4px;padding-bottom:4px;">
                    <div class="btn-group btn-group-sm">
                        <a href="javascript:void(0)" class="btn btn-light" title="Edit" onclick="return collection_manage('edit', '${i+1}');"><i class="fas fa-edit"></i></a>
                        <a href="javascript:void(0)" class="btn btn-light" title="Enable / disable" onclick="return collection_manage('toggle', '${i+1}');"><i class="fas fa-power-off"></i></a>
                        <a href="javascript:void(0)" class="btn btn-light" title="Delete" onclick="return collection_manage('delete', '${i+1}');"><i class="fas fa-trash"></i></a>
                    </div>
                </td>
            </tr>`;
        });
        if (rows.length > 0) {
            $("#collectionlist").html(output);
        } else if (filter) {
            $("#collectionlist").html('<tr><td colspan="9" class="text-muted p-3">No routes for this provider yet.</td></tr>');
        } else {
            $("#collectionlist").html($(".isEmpty").html());
        }
    }

    var collectionlist_check = function(){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "list" },
            success: function(data){
                ALL_ROUTES = data["routes"] || [];
                populateProviderFilter();
                renderRoutes();
            }, error: function(jqXHR){ quick_display_modal_error(jqXHR.responseText); }
        });
    };
    $(document).on('change', '#provider_filter', renderRoutes);
    collectionlist_check();
    loadConnectors();

    function simpleAction(cmd, id){
        $.ajax({ type: "POST", url: local_path + 'manage/',
            data: { csrfmiddlewaretoken: csrf, s: cmd, id: id },
            success: function(data){ toastr.success(data["message"], {closeButton:true, progressBar:true}); collectionlist_check(); },
            error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton:true, progressBar:true}); }
        });
    }

    window.collection_manage = function(cmd, index){
        index = index || -1;
        if (cmd == "add") {
            showThisBox(variant_boxes, add_modal_form);
            $(add_modal_form)[0].reset();
            loadConnectors();
            $("#collection_modal").modal("show");
        } else if (cmd == "edit") {
            showThisBox(variant_boxes, edit_modal_form);
            var data = ROUTES_DICT[index];
            loadConnectors(function(){
                var $f = $(edit_modal_form);
                $f.find("input[name=id]").val(data.id);
                $f.find("input[name=name]").val(data.name);
                $f.find("input[name=country]").val(data.country);
                $f.find("select[name=route_type]").val(data.route_type);
                $f.find("select[name=smpp_connector]").val(data.smpp_connector);
                // connector may no longer exist in the list; keep it selectable
                if ($f.find("select[name=smpp_connector]").val() !== data.smpp_connector) {
                    $f.find("select[name=smpp_connector]").append('<option value="'+esc(data.smpp_connector)+'" selected>'+esc(data.smpp_connector)+' (missing)</option>');
                }
                $f.find("input[name=buy_price]").val(data.buy_price);
                $f.find("input[name=currency]").val(data.currency);
                $f.find("input[name=tps]").val(data.tps);
                $f.find("select[name=status]").val(data.status);
            });
            $("#collection_modal").modal("show");
        } else if (cmd == "toggle") {
            simpleAction("toggle", ROUTES_DICT[index].id);
        } else if (cmd == "delete") {
            sweetAlert({
                title: global_trans["areyousuretodelete"],
                text: global_trans["youwontabletorevertthis"],
                type: 'warning', showCancelButton: true,
                cancelButtonClass: "btn btn-secondary m-btn m-btn--pill m-btn--icon",
                cancelButtonText: global_trans["no"],
                confirmButtonClass: "btn btn-danger m-btn m-btn--pill m-btn--air m-btn--icon",
                confirmButtonText: global_trans["yes"],
            }, function(isConfirm){ if (isConfirm) simpleAction("delete", ROUTES_DICT[index].id); });
        }
    };

    $("#add_new_obj").on('click', function(){ collection_manage('add'); });
    $(add_modal_form+","+edit_modal_form).on("submit", function(e){
        e.preventDefault();
        var serializeform = $(this).serialize();
        var inputs = $(this).find("input, select, button, textarea");
        $.ajax({ type: "POST", url: $(this).attr("action"), data: serializeform,
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
    $("li.nav-item.route_details-menu").addClass("active");
})(jQuery);
