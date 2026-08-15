(function($){
    var local_path = window.location.pathname, csrfmiddlewaretoken = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var add_modal_form = "#add_modal_form", edit_modal_form = "#edit_modal_form", service_modal_form = "#service_modal_form";
    var variant_boxes = [add_modal_form, edit_modal_form, service_modal_form];
    var SMPPCCM_DICT = {};
    var logsCid = null, logsTimer = null;
    var collectionlist_check = function() {
        $.ajax({
            url: local_path + 'manage/',
            type: "POST",
            data: {
                csrfmiddlewaretoken: csrfmiddlewaretoken,
                s: "list",

            },
            dataType: "json",
            success: function(data){
                // Sort recent: jcli lists oldest-first, so reverse for newest-added on top.
                var datalist = (data["connectors"] || []).slice().reverse();
                var output = $.map(datalist, function(val, i){
                    var html = "";
                    var maskedPassword = val.password ? '•'.repeat(Math.min(val.password.length, 8)) : '';
                    // Status dot reflects the ACTUAL SMPP bind, not just whether the
                    // service is running. Jasmin's "session" is BOUND_TRX/BOUND_TX/BOUND_RX
                    // only when the far-end SMSC has accepted the bind. A connector can be
                    // "started" yet sit at session=NONE/UNBOUND (far end down or rejecting),
                    // so keying green off status alone shows a false "connected".
                    //   green  = started AND bound      -> both sides established
                    //   amber  = started, not yet bound -> trying / rejected by peer
                    //   grey   = stopped
                    var isBound = /^BOUND/.test(val.session || "");
                    var isStarted = val.status === "started";
                    var dotClass, dotTitle;
                    if (isStarted && isBound) {
                        dotClass = "text-success"; dotTitle = "Bound (" + val.session + ")";
                    } else if (isStarted) {
                        dotClass = "text-warning"; dotTitle = "Started but not bound (" + (val.session || "NONE") + ")";
                    } else {
                        dotClass = "text-default"; dotTitle = "Stopped";
                    }
                    html += `<tr>
                        <td>${i+1}</td>
                        <td>${val.cid}</td>
                        <td>${val.host}</td>
                        <td>${val.port}</td>
                        <td>${val.username}</td>
                        <td><span class="password-masked" title="{% trans 'Password is masked for security' %}">${maskedPassword}</span></td>
                        <td class="text-center"><i class="fas fa-circle fa-lg ${dotClass}" title="${dotTitle}"></i></td>
                        <td class="text-center" style="padding-top:4px;padding-bottom:4px;">
                            <div class="btn-group btn-group-sm">
                                <a href="javascript:void(0)" class="btn btn-light" onclick="return collection_manage('service', '${i+1}');"><i class="fas fa-play-circle"></i></a>
                                <a href="javascript:void(0)" class="btn btn-light" title="View logs / status reason" onclick="return collection_manage('logs', '${i+1}');"><i class="fas fa-file-alt"></i></a>
                                <a href="javascript:void(0)" class="btn btn-light" onclick="return collection_manage('edit', '${i+1}');"><i class="fas fa-edit"></i></a>
                                <a href="javascript:void(0)" class="btn btn-light" onclick="return collection_manage('delete', '${i+1}');"><i class="fas fa-trash"></i></a>
                            </div>
                        </td>
                    </tr>`;
                    SMPPCCM_DICT[i+1] = val;
                    return html;
                });
                $("#collectionlist").html(datalist.length > 0 ? output : $(".isEmpty").html());
            }, error: function(jqXHR, textStatus, errorThrown){quick_display_modal_error(jqXHR.responseText);}
        })
    }
    collectionlist_check();
    window.collection_manage = function(cmd, index){
        index = index || -1;
        if (cmd == "add") {
            showThisBox(variant_boxes, add_modal_form);
            $("#collection_modal").modal("show");
        } else if (cmd == "edit") {
            showThisBox(variant_boxes, edit_modal_form);
            var data = SMPPCCM_DICT[index];
            $(edit_modal_form+" input[name=cid]").val(data.cid);
            $(edit_modal_form+" input[name=logfile]").val(data.logfile);
            $(edit_modal_form+" input[name=logrotate]").val(data.logrotate);
            $(edit_modal_form+" input[name=loglevel]").val(data.loglevel);
            $(edit_modal_form+" input[name=host]").val(data.host);
            $(edit_modal_form+" input[name=port]").val(data.port);
            $(edit_modal_form+" input[name=ssl]").val(data.ssl);
            $(edit_modal_form+" input[name=username]").val(data.username);
            $(edit_modal_form+" input[name=password]").val(data.password);
            $(edit_modal_form+" select[name=bind]").val(data.bind);
            $(edit_modal_form+" input[name=bind_to]").val(data.bind_to);
            $(edit_modal_form+" input[name=trx_to]").val(data.trx_to);
            $(edit_modal_form+" input[name=res_to]").val(data.res_to);
            $(edit_modal_form+" input[name=pdu_red_to]").val(data.pdu_red_to);
            $(edit_modal_form+" select[name=con_loss_retry]").val(data.con_loss_retry);
            $(edit_modal_form+" input[name=con_loss_delay]").val(data.con_loss_delay);
            $(edit_modal_form+" select[name=con_fail_retry]").val(data.con_fail_retry);
            $(edit_modal_form+" input[name=con_fail_delay]").val(data.con_fail_delay);
            $(edit_modal_form+" input[name=src_addr]").val(data.src_addr);
            $(edit_modal_form+" input[name=src_ton]").val(data.src_ton);
            $(edit_modal_form+" input[name=src_npi]").val(data.src_npi);
            $(edit_modal_form+" input[name=dst_ton]").val(data.dst_ton);
            $(edit_modal_form+" input[name=dst_npi]").val(data.dst_npi);
            $(edit_modal_form+" input[name=bind_ton]").val(data.bind_ton);
            $(edit_modal_form+" input[name=bind_npi]").val(data.bind_npi);
            $(edit_modal_form+" input[name=validity]").val(data.validity);
            $(edit_modal_form+" input[name=priority]").val(data.priority);
            $(edit_modal_form+" input[name=requeue_delay]").val(data.requeue_delay);
            $(edit_modal_form+" input[name=addr_range]").val(data.addr_range);
            $(edit_modal_form+" input[name=systype]").val(data.systype);
            $(edit_modal_form+" input[name=dlr_expiry]").val(data.dlr_expiry);
            $(edit_modal_form+" input[name=submit_throughput]").val(data.submit_throughput);
            $(edit_modal_form+" input[name=proto_id]").val(data.proto_id);
            $(edit_modal_form+" input[name=coding]").val(data.coding);
            $(edit_modal_form+" input[name=elink_interval]").val(data.elink_interval);
            $(edit_modal_form+" input[name=def_msg_id]").val(data.def_msg_id);
            $(edit_modal_form+" input[name=ripf]").val(data.ripf);
            $(edit_modal_form+" input[name=dlr_msgid]").val(data.dlr_msgid);
            $("#collection_modal").modal("show");
        } else if (cmd == "service") {
            showThisBox(variant_boxes, service_modal_form);
            var data = SMPPCCM_DICT[index];
            $(service_modal_form+" input[name=cid]").val(data.cid);
            $("#collection_modal").modal("show");
        } else if (cmd == "logs") {
            var data = SMPPCCM_DICT[index];
            logsCid = data.cid;
            $("#logs_modal_title").text("Logs — " + data.cid);
            $("#logs_errors_only").prop("checked", false);
            $("#logs_reason").removeClass("alert-success alert-warning").addClass("alert-info").text("Loading…");
            $("#logs_body").html('<div class="text-muted p-3">Loading…</div>');
            loadConnectorLogs();
            $("#logs_modal").modal("show");
        } else if (cmd == "delete") {
            sweetAlert({
                title: global_trans["areyousuretodelete"],
                text: global_trans["youwontabletorevertthis"],
                type: 'warning',
                showCancelButton: true,
                cancelButtonClass: "btn btn-secondary m-btn m-btn--pill m-btn--icon",
                cancelButtonText: global_trans["no"],
                confirmButtonClass: "btn btn-danger m-btn m-btn--pill m-btn--air m-btn--icon",
                confirmButtonText: global_trans["yes"],
            }, function(isConfirm){
                if (isConfirm) {
                    var data = SMPPCCM_DICT[index];
                    $.ajax({
                    	type: "POST",
                    	url: local_path + 'manage/',
                    	data: {
                    		csrfmiddlewaretoken: csrfmiddlewaretoken,
                    		s: cmd,
                    		cid: data.cid,
                    	},
                    	beforeSend: function(){},
						success: function(data){
							toastr.success(data["message"], {closeButton: true, progressBar: true,});
							collectionlist_check();
						},
						error: function(jqXHR, textStatus, errorThrown){
							toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton: true, progressBar: true,});
						}
                    })
                }
            });
        }
    }
    $("#add_new_obj").on('click', function(e){collection_manage('add');});
    $(add_modal_form+","+edit_modal_form+","+service_modal_form).on("submit", function(e){
        e.preventDefault();
        var serializeform = $(this).serialize();
		var inputs = $(this).find("input, select, button, textarea");
		//inputs.prop("disabled", true);
		$.ajax({
			type: "POST",
			url: $(this).attr("action"),
			data: serializeform,
			beforeSend: function(){inputs.prop("disabled", true);},
			success: function(data){
				toastr.success(data["message"], {closeButton: true, progressBar: true,});
				inputs.prop("disabled", false);
				$(".modal").modal("hide");
				collectionlist_check();
				//setTimeout(location.reload.bind(location), 2000);
			},
			error: function(jqXHR, textStatus, errorThrown){
				inputs.prop("disabled", false);
				toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton: true, progressBar: true,});
			}
		});
    });
    
    // Toggle password visibility
    $(document).on('click', '.toggle-password', function(e){
        e.preventDefault();
        var $button = $(this);
        var $input = $button.closest('.input-group').find('.password-input');
        var $icon = $button.find('i');
        
        if ($input.attr('type') === 'password') {
            $input.attr('type', 'text');
            $icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            $input.attr('type', 'password');
            $icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
    
    function escapeHtml(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }
    function loadConnectorLogs(){
        if(!logsCid) return;
        var errorsOnly = $("#logs_errors_only").is(":checked");
        $.ajax({
            url: local_path + 'manage/',
            type: "POST",
            data: { csrfmiddlewaretoken: csrfmiddlewaretoken, s: "logs", cid: logsCid, errors_only: errorsOnly, lines: 250 },
            dataType: "json",
            success: function(data){
                var reason = data.reason || "";
                var bound = /^Connected/i.test(reason);
                var $b = $("#logs_reason").removeClass("alert-success alert-warning alert-info");
                $b.addClass(bound ? "alert-success" : (data.available ? "alert-warning" : "alert-info"));
                $b.html('<i class="fas fa-'+(bound?'check-circle':'exclamation-triangle')+' mr-2"></i>'+ escapeHtml(reason));
                var lines = data.lines || [];
                if(!lines.length){
                    $("#logs_body").html('<div class="text-muted p-3">'+ (data.available ? 'No matching log lines.' : 'No log file yet.') +'</div>');
                } else {
                    var html = lines.map(function(ln){
                        var cls = (/\bERROR\b|Bind failed|ESME_/.test(ln)) ? 'log-err' : ((/\bWARNING\b/.test(ln)) ? 'log-warn' : '');
                        return '<div class="log-line '+cls+'">'+ escapeHtml(ln) +'</div>';
                    }).join('');
                    $("#logs_body").html(html);
                    var el = document.getElementById('logs_body'); if(el){ el.scrollTop = el.scrollHeight; }
                }
            },
            error: function(){ $("#logs_body").html('<div class="text-danger p-3">Failed to load logs.</div>'); }
        });
    }
    $("#logs_modal").on("shown.bs.modal", function(){
        if(logsTimer) clearInterval(logsTimer);
        logsTimer = setInterval(loadConnectorLogs, 5000);
    }).on("hidden.bs.modal", function(){
        if(logsTimer){ clearInterval(logsTimer); logsTimer = null; }
        logsCid = null;
    });
    $(document).on("change", "#logs_errors_only", function(){ loadConnectorLogs(); });
    $(document).on("click", "#logs_refresh", function(){ loadConnectorLogs(); });

    $("li.nav-item.smppccm-menu").addClass("active");
})(jQuery);