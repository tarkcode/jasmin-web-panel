(function($){
    var local_path = window.location.pathname, csrfmiddlewaretoken = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var add_modal_form = "#add_modal_form", edit_modal_form = "#edit_modal_form";
    var variant_boxes = [add_modal_form, edit_modal_form];
    var CONFIGS_DICT = {};
    var collectionlist_check = function(){
        $.ajax({
            url: local_path + 'manage/',
            type: "POST",
            data: {
                csrfmiddlewaretoken: csrfmiddlewaretoken,
                s: "list",

            },
            dataType: "json",
            success: function(data){
                var datalist = data["configs"];
                var output = $.map(datalist, function(val, i){
                    var html = "";
                    var statusDot = val.enabled
                        ? '<i class="fas fa-circle fa-lg text-success"></i>'
                        : '<i class="fas fa-circle fa-lg text-default"></i>';
                    var rateClass = val.success_rate >= 90 ? 'text-success' : (val.success_rate >= 50 ? 'text-warning' : 'text-danger');
                    var delayText = val.instant_response ? '<span class="badge badge-info">Instant</span>' : val.min_delay + 's – ' + val.max_delay + 's';
                    html += `<tr>
                        <td>${i+1}</td>
                        <td><strong>${val.cid}</strong></td>
                        <td>${val.name}</td>
                        <td class="text-center">${statusDot}</td>
                        <td class="text-center"><span class="${rateClass} font-weight-bold">${val.success_rate}%</span></td>
                        <td class="text-center">${delayText}</td>
                        <td class="text-center">
                            <span class="badge badge-light" title="Total">${val.total_messages}</span>
                            <span class="badge badge-success" title="Delivered">${val.delivered_count}</span>
                            <span class="badge badge-danger" title="Failed">${val.failed_count}</span>
                        </td>
                        <td class="text-center" style="padding-top:4px;padding-bottom:4px;">
                            <div class="btn-group btn-group-sm">
                            <a href="javascript:void(0)" class="btn btn-light" title="Edit" onclick="return collection_manage('edit', '${i+1}');"><i class="fas fa-edit"></i></a>
                            <a href="javascript:void(0)" class="btn btn-light" title="Toggle" onclick="return collection_manage('toggle', '${i+1}');"><i class="fas fa-power-off"></i></a>
                            <a href="javascript:void(0)" class="btn btn-light" title="Reset Stats" onclick="return collection_manage('reset_stats', '${i+1}');"><i class="fas fa-redo"></i></a>
                            <a href="javascript:void(0)" class="btn btn-light" title="Delete" onclick="return collection_manage('delete', '${i+1}');"><i class="fas fa-trash"></i></a>
                            </div>
                        </td>
                    </tr>`;
                    CONFIGS_DICT[i+1] = val;
                    return html;
                });
                $("#collectionlist").html(datalist.length > 0 ? output : $(".isEmpty").html());
            }, error: function(jqXHR, textStatus, errorThrown){quick_display_modal_error(jqXHR.responseText);}
        });
    }
    collectionlist_check();
    window.collection_manage = function(cmd, index){
        index = index || -1;
        if (cmd == "add") {
            showThisBox(variant_boxes, add_modal_form);
            $(add_modal_form)[0].reset();
            $("#add_enabled").prop("checked", true);
            $("#collection_modal").modal("show");
        } else if (cmd == "edit") {
            showThisBox(variant_boxes, edit_modal_form);
            var data = CONFIGS_DICT[index];
            $(edit_modal_form+" input[name=id]").val(data.id);
            $(edit_modal_form+" input[name=cid]").val(data.cid);
            $(edit_modal_form+" input[name=name]").val(data.name);
            $("#edit_enabled").prop("checked", data.enabled);
            $(edit_modal_form+" input[name=success_rate]").val(data.success_rate);
            $(edit_modal_form+" input[name=min_delay]").val(data.min_delay);
            $(edit_modal_form+" input[name=max_delay]").val(data.max_delay);
            $("#edit_instant_response").prop("checked", data.instant_response);
            $("#collection_modal").modal("show");
        } else if (cmd == "toggle") {
            var data = CONFIGS_DICT[index];
            $.ajax({
                type: "POST",
                url: local_path + 'manage/',
                data: {
                    csrfmiddlewaretoken: csrfmiddlewaretoken,
                    s: "toggle",
                    id: data.id,
                },
                beforeSend: function(){},
                success: function(data){
                    toastr.success(data["message"], {closeButton: true, progressBar: true,});
                    collectionlist_check();
                },
                error: function(jqXHR, textStatus, errorThrown){
                    toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton: true, progressBar: true,});
                }
            });
        } else if (cmd == "reset_stats") {
            var data = CONFIGS_DICT[index];
            $.ajax({
                type: "POST",
                url: local_path + 'manage/',
                data: {
                    csrfmiddlewaretoken: csrfmiddlewaretoken,
                    s: "reset_stats",
                    id: data.id,
                },
                beforeSend: function(){},
                success: function(data){
                    toastr.success(data["message"], {closeButton: true, progressBar: true,});
                    collectionlist_check();
                },
                error: function(jqXHR, textStatus, errorThrown){
                    toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton: true, progressBar: true,});
                }
            });
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
                    var data = CONFIGS_DICT[index];
                    $.ajax({
                    	type: "POST",
                    	url: local_path + 'manage/',
                    	data: {
                    		csrfmiddlewaretoken: csrfmiddlewaretoken,
                    		s: "delete",
                    		id: data.id,
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
    $(add_modal_form+","+edit_modal_form).on("submit", function(e){
        e.preventDefault();
        var serializeform = $(this).serialize();
		var inputs = $(this).find("input, select, button, textarea");
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
			},
			error: function(jqXHR, textStatus, errorThrown){
				inputs.prop("disabled", false);
				toastr.error(JSON.parse(jqXHR.responseText)["message"], {closeButton: true, progressBar: true,});
			}
		});
    });
    $("li.nav-item.fake_dlr-menu").addClass("active");
})(jQuery);
