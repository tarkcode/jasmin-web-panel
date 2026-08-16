(function($){
    var local_path = window.location.pathname, csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    function loadUsers(){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "users" },
            success: function(d){
                var opts = (d.users || []).slice().reverse().map(function(u){ return '<option value="'+esc(u)+'">'+esc(u)+'</option>'; }).join('');
                $(".user-select").html(opts || '<option value="">(no users)</option>');
            }
        });
    }

    var collectionlist_check = function(){
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "list" },
            success: function(data){
                var datalist = data["wallets"] || [];
                var output = $.map(datalist, function(val, i){
                    var bal = (val.jasmin_balance === null || val.jasmin_balance === undefined)
                        ? '<span class="text-muted" title="No quota set (unlimited/undefined)">ND</span>'
                        : esc(val.jasmin_balance);
                    return `<tr>
                        <td>${i+1}</td>
                        <td><strong>${esc(val.uid)}</strong></td>
                        <td class="text-right" style="font-variant-numeric:tabular-nums;">${bal}</td>
                        <td>${esc(val.currency)}</td>
                        <td class="text-center">${esc(val.txn_count)}</td>
                        <td class="text-center" style="padding-top:4px;padding-bottom:4px;">
                            <div class="btn-group btn-group-sm">
                                <a href="javascript:void(0)" class="btn btn-light" title="Credit" onclick="return wallet_txn('${esc(val.uid)}','credit','${esc(val.currency)}');"><i class="fas fa-plus"></i></a>
                                <a href="javascript:void(0)" class="btn btn-light" title="Debit" onclick="return wallet_txn('${esc(val.uid)}','debit','${esc(val.currency)}');"><i class="fas fa-minus"></i></a>
                                <a href="javascript:void(0)" class="btn btn-light" title="History" onclick="return wallet_history('${esc(val.uid)}');"><i class="fas fa-list"></i></a>
                            </div>
                        </td>
                    </tr>`;
                });
                $("#collectionlist").html(datalist.length > 0 ? output : $(".isEmpty").html());
            }, error: function(jqXHR){ quick_display_modal_error(jqXHR.responseText); }
        });
    };
    collectionlist_check();
    loadUsers();

    window.wallet_txn = function(uid, type, currency){
        loadUsers();
        setTimeout(function(){
            $("#txn_uid").val(uid || "");
            $("#txn_type").val(type || "credit");
            $("#txn_form input[name=amount]").val("0");
            $("#txn_form input[name=currency]").val(currency || "USD");
            $("#txn_form input[name=description]").val("");
            $("#txn_modal").modal("show");
        }, 150);
    };

    window.wallet_history = function(uid){
        $("#history_title").text("Transaction history — " + uid);
        $("#history_body").html('<tr><td colspan="6" class="text-muted">Loading…</td></tr>');
        $("#history_modal").modal("show");
        $.ajax({ url: local_path + 'manage/', type: "POST", dataType: "json",
            data: { csrfmiddlewaretoken: csrf, s: "history", uid: uid },
            success: function(d){
                var txns = d.transactions || [];
                if (!txns.length){ $("#history_body").html('<tr><td colspan="6" class="text-muted">No transactions.</td></tr>'); return; }
                var badge = { credit:'badge-success', refund:'badge-info', debit:'badge-warning', adjustment:'badge-secondary', sms_charge:'badge-light' };
                $("#history_body").html(txns.map(function(t){
                    var amt = parseFloat(t.amount);
                    var amtCls = amt >= 0 ? 'text-success' : 'text-danger';
                    var when = t.created ? t.created.replace('T',' ').substring(0,19) : '';
                    return '<tr>'+
                        '<td style="white-space:nowrap;">'+esc(when)+'</td>'+
                        '<td><span class="badge '+(badge[t.type]||'badge-secondary')+'">'+esc(t.type_display)+'</span></td>'+
                        '<td class="text-right '+amtCls+'" style="font-variant-numeric:tabular-nums;">'+esc(t.amount)+'</td>'+
                        '<td class="text-right" style="font-variant-numeric:tabular-nums;">'+(t.balance_after===null?'<span class="text-muted">—</span>':esc(t.balance_after))+'</td>'+
                        '<td>'+esc(t.description)+(t.reference?(' <small class="text-muted">'+esc(t.reference)+'</small>'):'')+'</td>'+
                        '<td>'+esc(t.by)+'</td></tr>';
                }).join(''));
            },
            error: function(){ $("#history_body").html('<tr><td colspan="6" class="text-danger">Failed to load.</td></tr>'); }
        });
    };

    $("#add_new_obj").on('click', function(){ wallet_txn('', 'credit', 'USD'); });

    $("#txn_form").on("submit", function(e){
        e.preventDefault();
        var inputs = $(this).find("input, select, button");
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

    $("#sync_sms_btn").on('click', function(){
        var $b = $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>Syncing…');
        $.ajax({ type: "POST", url: local_path + 'manage/', data: { csrfmiddlewaretoken: csrf, s: "sync_sms" },
            success: function(data){ toastr.success(data["message"], {closeButton:true, progressBar:true}); collectionlist_check(); },
            error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton:true, progressBar:true}); },
            complete: function(){ $b.prop('disabled', false).html('<i class="fas fa-sync-alt mr-1"></i>Sync SMS charges'); }
        });
    });
    $("li.nav-item.wallet-menu").addClass("active");
})(jQuery);
