(function($){
    var local_path = window.location.pathname, csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var add_modal_form = "#add_modal_form", edit_modal_form = "#edit_modal_form";
    var variant_boxes = [add_modal_form, edit_modal_form];
    var ASSIGN_DICT = {}, ROUTES = {}, ROUTES_LIST = [], USERS = [];

    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }
    function marginClass(m){ return m > 0 ? 'text-success' : (m < 0 ? 'text-danger' : 'text-muted'); }
    function statusBadge(val){
        return '<span class="badge ' + (val.status === 'active' ? 'badge-success' : 'badge-secondary') + '">' + esc(val.status_display) + '</span>';
    }

    function populateSelects(){
        var ropts = ROUTES_LIST.slice().reverse().map(function(r){
            return '<option value="' + r.id + '">' + esc(r.name) + ' — ' + esc(r.connector) +
                   ' (buy ' + esc(r.buy_price) + ' ' + esc(r.currency) + ')</option>';
        }).join('');
        $(".route-select").html(ropts || '<option value="">(no routes — add one in Route Details)</option>');
        var uopts = USERS.slice().reverse().map(function(u){ return '<option value="' + esc(u) + '">' + esc(u) + '</option>'; }).join('');
        $(".user-select").html(uopts || '<option value="">(no users)</option>');
    }

    function loadMeta(cb){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "meta" },
            success: function(d){
                ROUTES_LIST = d.routes || [];
                ROUTES = {};
                ROUTES_LIST.forEach(function(r){ ROUTES[r.id] = r; });
                USERS = d.users || [];
                populateSelects();
                if (cb) cb();
            }
        });
    }

    function updateMarginPreview($form){
        var r = ROUTES[$form.find('.route-select').val()];
        var sell = parseFloat($form.find('.sell-input').val());
        var $box = $form.find('.margin-preview');
        if (!r || isNaN(sell)){ $box.html('<span class="text-muted">Pick a route and enter a sell price.</span>'); return; }
        var buy = parseFloat(r.buy_price);
        var margin = sell - buy;
        var pct = buy > 0 ? (margin / buy * 100) : null;
        $box.html('Buy <strong>' + buy.toFixed(5) + ' ' + esc(r.currency) + '</strong> · Sell <strong>' +
            sell.toFixed(5) + ' ' + esc(r.currency) + '</strong> · Margin <strong class="' + marginClass(margin) + '">' +
            margin.toFixed(5) + ' ' + esc(r.currency) + (pct !== null ? (' (' + pct.toFixed(2) + '%)') : '') + '</strong>');
    }
    $(document).on('change', '.route-select', function(){ updateMarginPreview($(this).closest('form')); });
    $(document).on('input', '.sell-input', function(){ updateMarginPreview($(this).closest('form')); });

    var collectionlist_check = function(){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "list" },
            success: function(data){
                var datalist = data["assignments"] || [];
                var output = $.map(datalist, function(val, i){
                    ASSIGN_DICT[i+1] = val;
                    var m = parseFloat(val.margin);
                    var pct = (val.margin_pct === null || val.margin_pct === undefined) ? '<span class="text-muted">—</span>' : (val.margin_pct + '%');
                    return `<tr>
                        <td>${i+1}</td>
                        <td><strong>${esc(val.route_name)}</strong><br><small class="text-muted">${esc(val.connector)}${val.country ? ' · ' + esc(val.country) : ''}</small></td>
                        <td>${esc(val.uid)}</td>
                        <td class="text-right" style="font-variant-numeric:tabular-nums;">${esc(val.buy_price)} <span class="text-muted">${esc(val.currency)}</span></td>
                        <td class="text-right" style="font-variant-numeric:tabular-nums;">${esc(val.sell_price)} <span class="text-muted">${esc(val.currency)}</span></td>
                        <td class="text-right ${marginClass(m)}" style="font-variant-numeric:tabular-nums;font-weight:600;">${esc(val.margin)}</td>
                        <td class="text-right ${marginClass(m)}" style="font-variant-numeric:tabular-nums;">${pct}</td>
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
                $("#collectionlist").html(datalist.length > 0 ? output : $(".isEmpty").html());
            }, error: function(jqXHR){ quick_display_modal_error(jqXHR.responseText); }
        });
    };
    loadMeta();
    collectionlist_check();

    function simpleAction(cmd, id){
        $.ajax({ type: "POST", url: local_path + 'manage/', data: { csrfmiddlewaretoken: csrf, s: cmd, id: id },
            success: function(data){ toastr.success(data["message"], {closeButton:true, progressBar:true}); collectionlist_check(); },
            error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton:true, progressBar:true}); }
        });
    }

    window.collection_manage = function(cmd, index){
        index = index || -1;
        if (cmd == "add") {
            showThisBox(variant_boxes, add_modal_form);
            $(add_modal_form)[0].reset();
            loadMeta(function(){ updateMarginPreview($(add_modal_form)); });
            $("#collection_modal").modal("show");
        } else if (cmd == "edit") {
            showThisBox(variant_boxes, edit_modal_form);
            var data = ASSIGN_DICT[index];
            loadMeta(function(){
                var $f = $(edit_modal_form);
                $f.find("input[name=id]").val(data.id);
                $f.find("select[name=route_id]").val(data.route_id);
                $f.find("select[name=uid]").val(data.uid);
                if ($f.find("select[name=uid]").val() !== data.uid) {
                    $f.find("select[name=uid]").append('<option value="'+esc(data.uid)+'" selected>'+esc(data.uid)+'</option>');
                }
                $f.find("input[name=sell_price]").val(data.sell_price);
                $f.find("select[name=status]").val(data.status);
                $f.find("input[name=notes]").val(data.notes);
                updateMarginPreview($f);
            });
            $("#collection_modal").modal("show");
        } else if (cmd == "toggle") {
            simpleAction("toggle", ASSIGN_DICT[index].id);
        } else if (cmd == "delete") {
            sweetAlert({
                title: global_trans["areyousuretodelete"],
                text: global_trans["youwontabletorevertthis"],
                type: 'warning', showCancelButton: true,
                cancelButtonClass: "btn btn-secondary m-btn m-btn--pill m-btn--icon",
                cancelButtonText: global_trans["no"],
                confirmButtonClass: "btn btn-danger m-btn m-btn--pill m-btn--air m-btn--icon",
                confirmButtonText: global_trans["yes"],
            }, function(isConfirm){ if (isConfirm) simpleAction("delete", ASSIGN_DICT[index].id); });
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
    $("li.nav-item.route_assignments-menu").addClass("active");
})(jQuery);
